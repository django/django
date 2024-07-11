import unittest

from asgiref.sync import sync_to_async

from django.db import connection, new_connection
from django.test import TransactionTestCase

from .models import SimpleModel


@unittest.skipUnless(connection.supports_async is True, "Async DB test")
class AsyncSyncCominglingTest(TransactionTestCase):

    available_apps = ["async"]

    async def change_model_with_async(self, obj):
        async with new_connection() as conn:
            async with conn.acursor() as cursor:
                await cursor.aexecute(
                    """UPDATE "async_simplemodel" SET "field" = 10,"""
                    """ "created" = '2024-11-19 14:12:50.606384'::timestamp"""
                    """ WHERE "async_simplemodel"."id" = 1"""
                )

    async def test_transaction_async_comingling(self):
        s1 = await sync_to_async(SimpleModel.objects.create)(field=0)
        # with transaction.atomic():
        await self.change_model_with_async(s1)
