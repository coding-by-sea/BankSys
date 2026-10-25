"""
In-Memory Bank & Payment System
Actions
Theme: System
In-Memory Bank & Payment System

Reset chat

4
Build a simplified in-memory bank system, Bank, that supports accounts, transfers, spending analytics, scheduled payments, and account merging. Implement the following methods:

Accounts & transfers

create_account(account_id: str) -> None — creates a new account with balance 0. Raise ValueError if the account already exists.
deposit(account_id: str, amount: float) -> None — adds funds to an account. Raise ValueError for unknown accounts or non-positive amounts.
transfer(from_id: str, to_id: str, amount: float) -> None — moves funds between two accounts. Raise ValueError if either account doesn't exist, amount is non-positive, or from_id has insufficient balance. A successful transfer counts toward from_id's outgoing spending volume.
Analytics

get_top_k_spenders(k: int) -> list[str] — returns up to k account ids ordered by total outgoing transfer volume (descending). Ties break by account id ascending. Accounts with zero outgoing volume are excluded.
Scheduled payments

schedule_payment(payment_id: str, from_id: str, to_id: str, amount: float, timestamp: int) -> None — queues a transfer to execute at a given integer timestamp. Raise ValueError if payment_id is already in use or either account doesn't exist.
cancel_payment(payment_id: str) -> None — cancels a pending (not-yet-executed) scheduled payment. Raise ValueError if it doesn't exist or already executed.
advance_time(current_time: int) -> None — call this before any balance-affecting or analytics operation to execute all pending scheduled payments whose timestamp <= current_time, in timestamp order (ties broken by the order they were scheduled). A scheduled payment that fails validation at execution time (e.g. insufficient balance) is simply skipped — it does not raise, and does not retry.
Account merging

merge_accounts(id1: str, id2: str) -> str — merges id2 into id1: combines balances, combines outgoing spending volume (for top-k purposes), and reassigns any of id2's still-pending scheduled payments to id1 (as sender or recipient). After merging, id2 no longer exists as an independent account and any further operation referencing it raises ValueError. Returns id1.
Assume timestamps and calls arrive in non-decreasing time order from the caller's perspective — you don't need to handle out-of-order scheduling, just execute due payments before acting.
"""




from sortedcontainers import SortedList
from collections import defaultdict


class Bank:
    def __init__(self):
        # TODO: initialize your data structures
        self.balances = {}
        self.volumes = defaultdict(float)
        self.top_spenders = SortedList()

        self.schedule_in_order = SortedList()  # (timestamp, index)
        self.outgoing_scheduled_payments = defaultdict(set)  # from_id: set((timestamp, index))
        self.incoming_scheduled_payments = defaultdict(set)  # to_id: set((timestamp, index))
        self.scheduled_payments = dict()  # (timestamp, index): (from_id, to_id, amount, payment_id)
        self.payment_id_mapping = dict()  # payment_id: (timestamp, index)

        self.payment_index = 0

    # --- Level 1: Accounts & transfers ---
    def create_account(self, account_id: str) -> None:
        if account_id in self.balances:
            raise ValueError
        self.balances[account_id] = 0

    def deposit(self, account_id: str, amount: float) -> None:
        if account_id not in self.balances or amount <= 0:
            raise ValueError
        self.balances[account_id] += amount

    def transfer(self, from_id: str, to_id: str, amount: float) -> None:
        if (
            from_id not in self.balances
            or to_id not in self.balances
            or amount <= 0
            or amount > self.balances[from_id]
        ):
            raise ValueError
        self.balances[from_id] -= amount
        self.balances[to_id] += amount

        if from_id in self.volumes:
            total = self.volumes[from_id]
            self.top_spenders.remove((-total, from_id))

        self.volumes[from_id] += amount
        self.top_spenders.add((-self.volumes[from_id], from_id))

    # --- Level 2: Analytics ---
    def get_top_k_spenders(self, k: int) -> list:
        if k <= 0:
            return []
        return [y for (x, y) in self.top_spenders[:k]]

    # --- Level 3: Scheduled payments ---
    def schedule_payment(self, payment_id: str, from_id: str, to_id: str, amount: float, timestamp: int) -> None:
        if from_id not in self.balances or to_id not in self.balances or payment_id in self.payment_id_mapping:
            raise ValueError
        self.schedule_in_order.add((timestamp, self.payment_index))  # (timestamp, index)

        self.outgoing_scheduled_payments[from_id].add((timestamp, self.payment_index))
        self.incoming_scheduled_payments[to_id].add((timestamp, self.payment_index))
        self.scheduled_payments[(timestamp, self.payment_index)] = (from_id, to_id, amount, payment_id)
        self.payment_id_mapping[payment_id] = (timestamp, self.payment_index)

        self.payment_index += 1

    def _remove_pending_payment(self, key: tuple) -> None:
        from_id, to_id, _amount, payment_id = self.scheduled_payments.pop(key)
        self.schedule_in_order.remove(key)

        self.outgoing_scheduled_payments[from_id].remove(key)
        if not self.outgoing_scheduled_payments[from_id]:
            del self.outgoing_scheduled_payments[from_id]

        self.incoming_scheduled_payments[to_id].remove(key)
        if not self.incoming_scheduled_payments[to_id]:
            del self.incoming_scheduled_payments[to_id]

        del self.payment_id_mapping[payment_id]

    def cancel_payment(self, payment_id: str) -> None:
        if payment_id not in self.payment_id_mapping:
            raise ValueError
        key = self.payment_id_mapping[payment_id]
        self._remove_pending_payment(key)

    def advance_time(self, current_time: int) -> None:
        while self.schedule_in_order:
            if self.schedule_in_order[0][0] <= current_time:
                key = self.schedule_in_order[0]
                from_id, to_id, amount, _payment_id = self.scheduled_payments[key]
                try:
                    self.transfer(from_id, to_id, amount)
                except ValueError:
                    pass
                self._remove_pending_payment(key)
            else:
                break

    # --- Level 4: Merging ---
    def merge_accounts(self, id1: str, id2: str) -> str:
        if id1 == id2 or id1 not in self.balances or id2 not in self.balances:
            raise ValueError

        id1_volume = self.volumes.get(id1, 0)
        id2_volume = self.volumes.get(id2, 0)
        for account_id, volume in ((id1, id1_volume), (id2, id2_volume)):
            if volume:
                self.top_spenders.remove((-volume, account_id))

        merged_volume = id1_volume + id2_volume
        if merged_volume:
            self.volumes[id1] = merged_volume
            self.top_spenders.add((-merged_volume, id1))
        else:
            self.volumes.pop(id1, None)
        self.volumes.pop(id2, None)

        self.balances[id1] += self.balances[id2]
        del self.balances[id2]

        outgoing_keys = self.outgoing_scheduled_payments.pop(id2, set())
        for key in outgoing_keys:
            from_id, to_id, amount, payment_id = self.scheduled_payments[key]
            self.scheduled_payments[key] = (id1, to_id, amount, payment_id)
            self.outgoing_scheduled_payments[id1].add(key)

        incoming_keys = self.incoming_scheduled_payments.pop(id2, set())
        for key in incoming_keys:
            from_id, to_id, amount, payment_id = self.scheduled_payments[key]
            self.scheduled_payments[key] = (from_id, id1, amount, payment_id)
            self.incoming_scheduled_payments[id1].add(key)

        return id1


if __name__ == "__main__":
    bank = Bank()
    bank.create_account("alice")
    bank.create_account("bob")
    bank.deposit("alice", 100)
    bank.transfer("alice", "bob", 40)
    print(bank.get_top_k_spenders(1))  # ['alice']
