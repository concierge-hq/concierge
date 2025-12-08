from concierge.core import State, stage, task, workflow


@stage(name="transaction")
class TransactionStage:
    @task(description="Create payment request")
    def create_payment(self, state: State, amount: float, recipient: str) -> dict:
        return {"payment_id": "PAY123"}

    @task(description="Request money")
    def request_money(self, state: State, amount: float, recipient: str, note: str) -> dict:
        return {"request_id": "REQ123"}


@stage(name="review", prerequisites=["payment.amount", "payment.recipient"])
class ReviewStage:
    @task(description="Review payment details")
    def review_payment(self, state: State) -> dict:
        return {"details": {}}

    @task(description="Add payment note")
    def add_note(self, state: State, note: str) -> dict:
        return {"saved": True}

    @task(description="Select funding source")
    def select_source(self, state: State, source: str) -> dict:
        return {"source": source}


@stage(name="verification")
class VerificationStage:
    @task(description="Verify with 2FA code")
    def verify_2fa(self, state: State, code: str) -> dict:
        return {"verified": True}

    @task(description="Verify with biometric")
    def verify_biometric(self, state: State) -> dict:
        return {"verified": True}


@stage(name="confirmation", prerequisites=["verification.status"])
class ConfirmationStage:
    @task(description="Confirm and send payment")
    def confirm_payment(self, state: State) -> dict:
        return {"transaction_id": "TXN123", "status": "completed"}

    @task(description="Cancel payment")
    def cancel_payment(self, state: State) -> dict:
        return {"cancelled": True}


@workflow(name="payment")
class PaymentWorkflow:
    transaction = TransactionStage
    review = ReviewStage
    verification = VerificationStage
    confirmation = ConfirmationStage

    transitions = {
        transaction: [review],
        review: [verification, transaction],
        verification: [confirmation],
        confirmation: [],
    }
