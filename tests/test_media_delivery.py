import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from media_delivery import deliver_visit


class FakeClient:
    def __init__(self):
        self.calls = []

    def merge(self, inputs, operation_id):
        self.calls.append(("merge", inputs, operation_id))
        return {"ok": True, "data": {"job_id": "merge-job", "pdf_id": "merged-pdf", "url": "data:application/pdf;base64,merged"}, "metadata": {}}

    def split(self, pdf, pages, operation_id):
        self.calls.append(("split", pdf, pages, operation_id))
        return {"ok": True, "data": {"job_id": "split-job"}, "metadata": {}}

    def queue_publish(self, queue, payload, operation_id):
        self.calls.append(("queue", queue, payload, operation_id))
        return {"ok": True, "data": {"message_id": "delivery-message"}, "metadata": {}}


def test_visit_groups_become_one_queued_creator_delivery():
    client = FakeClient()
    result = deliver_visit(
        client,
        {"visit_id": "visit-2048", "inputs": ["triage.pdf", "consent.pdf"], "page_groups": [[1], [2]]},
    )

    assert result == {"visit_id": "visit-2048", "group_count": 2, "queued": {"message_id": "delivery-message"}}
    assert client.calls[1] == ("split", "data:application/pdf;base64,merged", [[1, 1], [2, 2]], "split:visit-2048")
    assert client.calls[2][1] == "creator-media-delivery"
