"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    def test_account_not_found(self):
        """It should not Read an Account that is not found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...

    def test_read_an_account(self):
        """It should READ an Account by id (happy path)"""
        acct = AccountFactory()
        # create first
        r = self.client.post(
            BASE_URL, json=acct.serialize(), content_type="application/json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        account_id = r.get_json()["id"]

        # read it back
        resp = self.client.get(f"{BASE_URL}/{account_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.get_json()
        self.assertEqual(body["id"], account_id)
        self.assertEqual(body["name"], acct.name)
        self.assertEqual(body["email"], acct.email)
        self.assertEqual(body["address"], acct.address)
        self.assertEqual(body["phone_number"], acct.phone_number)
        self.assertEqual(body["date_joined"], str(acct.date_joined))

    def test_list_accounts(self):
        """It should LIST all Accounts"""
        a1 = AccountFactory()
        a2 = AccountFactory()
        self.client.post(BASE_URL, json=a1.serialize(), content_type="application/json")
        self.client.post(BASE_URL, json=a2.serialize(), content_type="application/json")

        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertGreaterEqual(len(data), 2)

    def test_update_account(self):
        """It should UPDATE an existing Account"""
        acct = AccountFactory()
        r = self.client.post(
            BASE_URL, json=acct.serialize(), content_type="application/json"
        )
        account_id = r.get_json()["id"]

        payload = acct.serialize()
        payload["name"] = "Updated Name"

        resp = self.client.put(
            f"{BASE_URL}/{account_id}",
            json=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["name"], "Updated Name")

    def test_update_account_not_found(self):
        """It should return 404 when updating a missing Account"""
        payload = AccountFactory().serialize()
        resp = self.client.put(
            f"{BASE_URL}/0", json=payload, content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_wrong_media_type(self):
        """It should return 415 when media type is wrong"""
        acct = AccountFactory()
        r = self.client.post(
            BASE_URL, json=acct.serialize(), content_type="application/json"
        )
        account_id = r.get_json()["id"]

        # triggers check_content_type("application/json") -> 415
        resp = self.client.put(
            f"{BASE_URL}/{account_id}",
            data="{}",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_account(self):
        """It should DELETE an Account"""
        acct = AccountFactory()
        r = self.client.post(
            BASE_URL, json=acct.serialize(), content_type="application/json"
        )
        account_id = r.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{account_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # verify it's gone
        self.assertEqual(
            self.client.get(f"{BASE_URL}/{account_id}").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_account_not_found(self):
        """It should return 404 when deleting a missing Account"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(
            resp.status_code,
            status.HTTP_404_NOT_FOUND,
        )

