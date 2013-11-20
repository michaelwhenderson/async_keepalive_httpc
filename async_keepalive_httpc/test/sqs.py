import os

import boto.sqs
import yaml
from tornado.testing import AsyncTestCase, gen_test
import shortuuid

from async_keepalive_httpc.aws.sqs import SQSQueue
from async_keepalive_httpc.aws.auth import EasyV4Sign, IamRoleV4Sign



class SQSTestCase(AsyncTestCase):

    _region = 'ap-southeast-2'
    _q_name = 'unittest_q'


    def setUp(self):
        super(SQSTestCase, self).setUp()
        path = os.path.abspath(
            os.path.join (
                os.path.dirname(__file__), 'aws_keypair.yaml' 
            )
        )

        is_using_meta = False

        if os.path.isfile(path):

            with open(path, 'rb') as f:
                d = yaml.load(f.read())
                self.Q_URL = d['Q_URL']
                self.ACCESS_KEY = d['ACCESS_KEY']
                self.SECRET_KEY = d['SECRET_KEY']

            self.boto_conn = boto.sqs.connect_to_region(
                self._region,
                aws_access_key_id=self.ACCESS_KEY,
                aws_secret_access_key=self.SECRET_KEY)

        else:
            is_using_meta = True
            self.boto_conn = boto.sqs.connect_to_region(self._region)

        self.boto_q = self.boto_conn.get_queue(self._q_name) 
        if not self.boto_q:
            self.boto_q = self.boto_conn.create_queue(self._q_name)

        if not is_using_meta:
            self.q = SQSQueue(
                self.io_loop,
                self.Q_URL,
                access_key = self.ACCESS_KEY,
                secret_key= self.SECRET_KEY,
                endpoint=self._region
            )
        else:
            signer = IamRoleV4Sign(
                'sqs',
                self.io_loop,
                endpoint = self._region
            )

            self.q = SQSQueue(
                self.io_loop,
                self.Q_URL,
                signer = signer,
                endpoint=self._region,
            )

    # def tearDown(self):
    #     while(True)

    @gen_test(timeout=100)
    def test_send(self):

        r1 = yield self.q.send('abc')
        r2 = yield self.q.send('cde')
        r3 = yield self.q.send('fgh')

        self.assertEqual(r1.code, 200)
        self.assertEqual(r2.code, 200)
        self.assertEqual(r3.code, 200)

        # make sure it is 'keep-alive'
        self.assertEqual(self.q.client.connection.connect_times, 1)

    @gen_test(timeout=100)
    def test_send_batch(self):
        r1 = yield self.q.send_batch(messages=['1abc', '2def', '3ghi'])
        self.assertEqual(r1.code, 200)

        # make sure it is 'keep-alive'
        self.assertEqual(self.q.client.connection.connect_times, 1)

    @gen_test(timeout=100)
    def test_send_batch_with_signer(self):
        signer = EasyV4Sign(
            self.ACCESS_KEY,
            self.SECRET_KEY,
            'sqs'
        )

        q = SQSQueue(self.io_loop, self.Q_URL, signer=signer)

        r1 = yield q.send_batch(messages=['1abc', '2def', '3ghi'])
        self.assertEqual(r1.code, 200)

        # make sure it is 'keep-alive'
        self.assertEqual(q.client.connection.connect_times, 1)
