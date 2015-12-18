from django.test import TestCase

from participants.models import Participant
from submissions.models import Submission, SubmissionFile


class BrainsTests(TestCase):

    def test_index_page_works(self):
        response = self.client.get("/")
        assert response.content == "Hello, I process submissions!"

    def test_submissions_list_empty_returns_404(self):
        response = self.client.get("/submissions/list/")
        assert response.status_code == 404

    def test_submissions_list_returns_proper_data(self):
        participant = Participant.objects.create(name="test")
        submission = Submission.objects.create(
            participant=participant,
            description="test #1"
        )
        response = self.client.get("/submissions/list/")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["submitter"] == "test"
        assert data[0]["languages"] == ""
        assert data[0]["id"] == 1
        assert data[0]["description"] == "test #1"

    def test_submissions_detail_returns_404(self):
        response = self.client.get("/submissions/detail/0")
        assert response.status_code == 404

    def test_submissions_detail_returns_proper_data(self):
        participant = Participant.objects.create(name="test")
        submission = Submission.objects.create(
            participant=participant,
            description="test #1"
        )

        response = self.client.get("/submissions/detail/0")


