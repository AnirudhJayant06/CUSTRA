"""Emulator-only subprocess fixture; never deployed or used by the application."""

import asyncio
import json
import os
import sys

import httpx

from app.agents.consumer import answer_text
from app.models.exchange import ValidatedAnswer
from app.services.a2a_gateway import A2AGateway
from app.services.cases import CaseService
from app.services.repository import FirestoreCaseStore, FirestoreVaultStore
from app.services.vault import VaultService
from main import create_app as business_app
from store import FirestoreReplayStore


class FictionalConsumer:
    async def answer(self, question, facts, transcript):
        return ValidatedAnswer(text=answer_text(question.requested_fields, facts),
                               field_refs=question.requested_fields)


async def main():
    host = os.getenv('FIRESTORE_EMULATOR_HOST', '')
    if not host.startswith(('127.0.0.1:', 'localhost:', '[::1]:')):
        raise RuntimeError('A loopback emulator is required')
    namespace, phase = sys.argv[1:]
    vault = VaultService(FirestoreVaultStore('demo-custra-tests', namespace))
    cases = FirestoreCaseStore('demo-custra-tests', namespace)
    simulator = business_app('http://business.test', FirestoreReplayStore('demo-custra-tests', namespace))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=simulator), base_url='http://business.test') as client:
        service = CaseService(vault, cases, consumer=FictionalConsumer(), gateway=A2AGateway('http://business.test', client))
        if phase == 'start':
            vault.save_profile({'name': 'Fictional User', 'phone': '9999999999', 'email': 'fictional@example.test'})
            vault.seed_demo_address()
            product = vault.create_product({'categoryId': 'smartphone', 'brandId': 'samsung', 'displayName': 'Fictional Phone'})
            case = service.create({'productId': product['id'], 'addressId': 'demo-address',
                                   'issueSummary': 'Fictional fault', 'description': 'The fictional device stops.'},
                                  'fictional-restart-creation-key')
            for _ in range(2):
                case = await service.advance(case['id'], case['currentVersion'])
            assert case['businessStage'] == 'issue'
        else:
            case = cases.list()[0]
            for _ in range(3):
                case = await service.advance(case['id'], case['currentVersion'])
            assert case['status'] == 'AWAITING_APPOINTMENT'
            case = await service.book(case['id'], service.slots(case['id'])[0]['id'], 'fictional-restart-booking-key')
            assert case['status'] == 'BOOKED'
        events = cases.events(case['id'])
        print(json.dumps({'id': case['id'], 'status': case['status'], 'stage': case['businessStage'],
                          'context': case['protocolContextId'], 'events': [event['eventId'] for event in events]}))


if __name__ == '__main__':
    asyncio.run(main())
