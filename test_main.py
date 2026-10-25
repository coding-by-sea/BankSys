import unittest

from main import Bank


class AdvanceTimeTests(unittest.TestCase):
    def setUp(self):
        self.bank = Bank()
        for account_id in ("alice", "bob", "carol"):
            self.bank.create_account(account_id)

    def test_does_not_process_a_payment_before_its_due_time(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)

        self.bank.advance_time(9)

        self.assertEqual(self.bank.balances["alice"], 100)
        self.assertEqual(self.bank.balances["bob"], 0)

    def test_processes_due_payments_and_updates_spending_analytics(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)

        self.bank.advance_time(10)

        self.assertEqual(self.bank.balances["alice"], 60)
        self.assertEqual(self.bank.balances["bob"], 40)
        self.assertEqual(self.bank.get_top_k_spenders(1), ["alice"])

    def test_processes_all_overdue_payments_including_same_timestamp(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 10, timestamp=5)
        self.bank.schedule_payment("p2", "alice", "carol", 20, timestamp=10)
        self.bank.schedule_payment("p3", "alice", "bob", 30, timestamp=10)

        self.bank.advance_time(10)

        self.assertEqual(self.bank.balances["alice"], 40)
        self.assertEqual(self.bank.balances["bob"], 40)
        self.assertEqual(self.bank.balances["carol"], 20)

    def test_does_not_process_a_payment_more_than_once(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)

        self.bank.advance_time(10)
        self.bank.advance_time(10)

        self.assertEqual(self.bank.balances["alice"], 60)
        self.assertEqual(self.bank.balances["bob"], 40)

    def test_processed_payment_is_removed_from_all_pending_indexes(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)
        key = self.bank.payment_id_mapping["p1"]

        self.bank.advance_time(10)

        self.assertNotIn(key, self.bank.schedule_in_order)
        self.assertNotIn(key, self.bank.scheduled_payments)
        self.assertNotIn("p1", self.bank.payment_id_mapping)
        self.assertNotIn("alice", self.bank.outgoing_scheduled_payments)
        self.assertNotIn("bob", self.bank.incoming_scheduled_payments)

    def test_skips_a_due_payment_when_the_sender_lacks_funds(self):
        self.bank.deposit("alice", 30)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)

        self.bank.advance_time(10)

        self.assertEqual(self.bank.balances["alice"], 30)
        self.assertEqual(self.bank.balances["bob"], 0)
        self.assertEqual(self.bank.get_top_k_spenders(1), [])

    def test_skipped_payment_is_removed_from_all_pending_indexes(self):
        self.bank.deposit("alice", 30)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)
        key = self.bank.payment_id_mapping["p1"]

        self.bank.advance_time(10)

        self.assertNotIn(key, self.bank.schedule_in_order)
        self.assertNotIn(key, self.bank.scheduled_payments)
        self.assertNotIn("p1", self.bank.payment_id_mapping)
        self.assertNotIn("alice", self.bank.outgoing_scheduled_payments)
        self.assertNotIn("bob", self.bank.incoming_scheduled_payments)

    def test_cancelled_payment_is_removed_without_affecting_other_payments(self):
        self.bank.deposit("alice", 100)
        self.bank.schedule_payment("p1", "alice", "bob", 40, timestamp=10)
        self.bank.schedule_payment("p2", "alice", "carol", 20, timestamp=10)
        cancelled_key = self.bank.payment_id_mapping["p1"]
        remaining_key = self.bank.payment_id_mapping["p2"]

        self.bank.cancel_payment("p1")

        self.assertNotIn(cancelled_key, self.bank.schedule_in_order)
        self.assertNotIn(cancelled_key, self.bank.scheduled_payments)
        self.assertNotIn("p1", self.bank.payment_id_mapping)
        self.assertIn(remaining_key, self.bank.schedule_in_order)
        self.assertIn(remaining_key, self.bank.scheduled_payments)
        self.bank.advance_time(10)
        self.assertEqual(self.bank.balances["carol"], 20)


class MergeAccountsTests(unittest.TestCase):
    def setUp(self):
        self.bank = Bank()
        for account_id in ("alice", "bob", "carol"):
            self.bank.create_account(account_id)

    def test_merge_combines_balances_and_removes_the_absorbed_account(self):
        self.bank.deposit("alice", 40)
        self.bank.deposit("bob", 60)

        result = self.bank.merge_accounts("alice", "bob")

        self.assertEqual(result, "alice")
        self.assertEqual(self.bank.balances["alice"], 100)
        self.assertNotIn("bob", self.bank.balances)
        with self.assertRaises(ValueError):
            self.bank.deposit("bob", 1)

    def test_merge_combines_spending_volume_for_top_spenders(self):
        self.bank.deposit("alice", 40)
        self.bank.deposit("bob", 60)
        self.bank.transfer("alice", "carol", 20)
        self.bank.transfer("bob", "carol", 30)

        self.bank.merge_accounts("alice", "bob")

        self.assertEqual(self.bank.get_top_k_spenders(1), ["alice"])

    def test_merge_reassigns_pending_outgoing_and_incoming_payments(self):
        self.bank.deposit("bob", 50)
        self.bank.deposit("carol", 60)
        self.bank.schedule_payment("outgoing", "bob", "carol", 10, timestamp=10)
        self.bank.schedule_payment("incoming", "carol", "bob", 20, timestamp=10)

        self.bank.merge_accounts("alice", "bob")
        self.bank.advance_time(10)

        self.assertEqual(self.bank.balances["alice"], 50)
        self.assertEqual(self.bank.balances["carol"], 50)


if __name__ == "__main__":
    unittest.main()
