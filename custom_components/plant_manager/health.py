"""Explicit photo checks via the existing Pl@ntNet free account.

No background analysis, paid provider or key exposed to the frontend. Extra
tables are inside the existing SQLite database and therefore in its backups.
"""
from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone
import uuid

import aiohttp
from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PLANTNET_API_KEY
from .db import NotFoundError
from .http import _read_file
from .manager import get_manager, image_extension

API = 'https://my-api.plantnet.org/v2'
TIMEOUT = aiohttp.ClientTimeout(total=45)
MAX_IMAGE = 10 * 1024 * 1024
LOCK_KEY = 'plant_manager_health_lock'


class CheckError(Exception):
    """Only fixed, non-secret messages leave this module."""


def free_quota(subscription: dict, daily: dict) -> dict:
    """Fail closed if the account cannot be established as a free account."""
    contract = subscription.get('contract') or {}
    if not isinstance(contract, dict):
        contract = {}
    plan = contract.get('plan') or subscription.get('plan')
    q = daily.get('quota', {}).get('identify', {})
    remaining, total = q.get('remaining'), q.get('total')
    # Free accounts cannot access the contract endpoint (403). A successful
    # authenticated quota response with exactly the documented 500/day quota
    # establishes that standard free access; an explicit paid plan is rejected.
    standard_free = plan is None and subscription.get('contract_restricted') is True and type(total) is int and total == 500
    if str(plan).lower() != 'free' and not standard_free:
        raise CheckError('Der kostenlose Pl@ntNet-Tarif konnte nicht bestätigt werden. Es wurde kein Foto gesendet.')
    if type(remaining) is not int or type(total) is not int or not 0 < total <= 500:
        raise CheckError('Das kostenlose Tageskontingent konnte nicht bestätigt werden. Es wurde kein Foto gesendet.')
    if remaining < 1:
        raise CheckError('Das kostenlose Tageskontingent ist aufgebraucht. Bitte morgen erneut versuchen.')
    return {'remaining': remaining, 'total': total, 'plan': 'free'}


def candidates_from(payload: dict) -> list[dict]:
    """Keep only bounded, renderable suggestions, never a healthy verdict."""
    out = []
    rows = payload.get('results', [])
    if not isinstance(rows, list):
        raise CheckError('Pl@ntNet hat keine auswertbare Ergebnisliste geliefert.')
    for row in rows[:5]:
        if not isinstance(row, dict):
            continue
        try:
            score = float(row.get('score', 0))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score) or not 0 <= score <= 1:
            continue
        code = str(row.get('name') or '')[:40]
        label = str(row.get('description') or row.get('label') or code)[:600]
        if code and label:
            out.append({'code': code, 'label': label, 'score': score})
    return sorted(out, key=lambda r: r['score'], reverse=True)


async def _api(session, key: str, route: str, data=None) -> dict:
    """Do not propagate aiohttp exceptions: their URLs contain the API key."""
    params = {'api-key': key}
    if data is not None:
        params.update({'lang': 'de', 'nb-results': '5', 'include-related-images': 'false'})
    method = session.post if data is not None else session.get
    try:
        async with method(API + route, params=params, data=data, timeout=TIMEOUT) as resp:
            if resp.status == 403 and route == '/subscription':
                return {'contract_restricted': True}
            if resp.status in (401, 403):
                raise CheckError('Pl@ntNet hat den vorhandenen Zugang abgelehnt.')
            if resp.status == 429:
                raise CheckError('Das kostenlose Tageskontingent ist aufgebraucht. Bitte morgen erneut versuchen.')
            if resp.status == 404 and data is not None:
                return {'results': []}
            if resp.status >= 400:
                raise CheckError('Pl@ntNet konnte die Anfrage nicht ausführen. Bitte später erneut versuchen.')
            value = await resp.json()
            if not isinstance(value, dict):
                raise CheckError('Pl@ntNet hat eine unerwartete Antwort geliefert.')
            return value
    except (aiohttp.ClientError, TimeoutError, ValueError):
        raise CheckError('Pl@ntNet ist gerade nicht erreichbar oder hat keine lesbare Antwort geliefert.') from None


def _history(manager, plant_id: str) -> list[dict]:
    db = manager.db
    with db._lock:
        with db.conn:
            db.conn.execute('''CREATE TABLE IF NOT EXISTS garden_health_checks (
                id TEXT PRIMARY KEY, plant_id TEXT NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
                checked_at TEXT NOT NULL, result TEXT NOT NULL)''')
        return [json.loads(row[0]) for row in db.conn.execute(
            'SELECT result FROM garden_health_checks WHERE plant_id=? ORDER BY checked_at DESC LIMIT 20', (plant_id,))]


def _save(manager, plant_id: str, record: dict) -> None:
    with manager.db._lock, manager.db.conn:
        manager.db.conn.execute('INSERT INTO garden_health_checks VALUES (?,?,?,?)',
            (record['id'], plant_id, record['checked_at'], json.dumps(record, ensure_ascii=False)))


class HealthView(HomeAssistantView):
    url = '/api/plant_manager/health/{plant_id}'
    name = 'api:plant_manager:health'
    requires_auth = True

    async def _context(self, request, plant_id):
        manager = get_manager(request.app[KEY_HASS])
        if manager is None:
            raise CheckError('Die Pflanzenverwaltung ist noch nicht geladen.')
        plant = await manager._run(manager.db.get_plant, plant_id)
        return manager, plant

    async def _quota(self, request, manager):
        key = manager.options.get(CONF_PLANTNET_API_KEY)
        if not key:
            raise CheckError('Für die kostenlose Fotoprüfung fehlt der Pl@ntNet-Zugang.')
        session = async_get_clientsession(request.app[KEY_HASS])
        sub = await _api(session, key, '/subscription')
        daily = await _api(session, key, '/quota/daily')
        return session, key, free_quota(sub, daily)

    async def get(self, request, plant_id):
        """History and a free-plan preflight; no image inference on GET."""
        try:
            manager, plant = await self._context(request, plant_id)
            checks = await manager._run(_history, manager, plant_id)
            result = {'checks': checks, 'ready': False,
                      'coverage': 'documented' if (plant.get('species') or '').lower() == 'coffea arabica' else 'unconfirmed'}
            try:
                _, _, quota = await self._quota(request, manager)
                result.update(ready=True, quota=quota)
            except CheckError as err:
                result['message'] = str(err)
            return self.json(result)
        except NotFoundError:
            return self.json_message('Die Pflanze wurde nicht gefunden.', 404)
        except CheckError as err:
            return self.json_message(str(err), 503)

    async def post(self, request, plant_id):
        hass = request.app[KEY_HASS]
        lock = hass.data.setdefault(LOCK_KEY, asyncio.Lock())
        if lock.locked():
            return self.json_message('Eine Fotoprüfung läuft bereits. Bitte kurz warten.', 429)
        try:
            async with lock:
                manager, plant = await self._context(request, plant_id)
                data = await _read_file(request, MAX_IMAGE)
                if not data:
                    return self.json_message('Bitte ein aktuelles Foto auswählen.', 400)
                extension = image_extension(data)
                if extension not in ('jpg', 'jpeg', 'png'):
                    return self.json_message('Bitte ein JPEG- oder PNG-Foto verwenden.', 415)
                # This must precede the only inference call, every time.
                session, key, quota = await self._quota(request, manager)
                await manager._run(_history, manager, plant_id)
                form = aiohttp.FormData()
                form.add_field('images', data, filename='plant.' + extension,
                               content_type='image/png' if extension == 'png' else 'image/jpeg')
                form.add_field('organs', 'auto')
                payload = await _api(session, key, '/diseases/identify', form)
                candidates = candidates_from(payload)
                photo = await manager.async_add_photo(plant_id, data, 'health-check')
                record = {'id': uuid.uuid4().hex, 'checked_at': datetime.now(timezone.utc).isoformat(),
                          'provider': 'Pl@ntNet', 'species': plant.get('species'),
                          'photo_id': photo['id'], 'candidates': candidates,
                          'coverage': 'documented' if (plant.get('species') or '').lower() == 'coffea arabica' else 'unconfirmed',
                          'remaining': payload.get('remainingIdentificationRequests', max(0, quota['remaining']-1))}
                await manager._run(_save, manager, plant_id, record)
                notes = 'Fotoprüfung (Pl@ntNet), keine Diagnose. ' + (
                    'Mögliche Ursachen: ' + '; '.join(c['label'] for c in candidates[:3]) if candidates else
                    'Kein auswertbarer Treffer. Das ist keine Bestätigung, dass die Pflanze gesund ist.')
                await manager.async_log(plant_id, 'note', notes=notes, source='health-check')
                return self.json(record)
        except NotFoundError:
            return self.json_message('Die Pflanze wurde nicht gefunden.', 404)
        except CheckError as err:
            return self.json_message(str(err), 400)
        except ValueError:
            return self.json_message('Das Foto ist zu groß oder das Dateiformat wird nicht unterstützt.', 413)
