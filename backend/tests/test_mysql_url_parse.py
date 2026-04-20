"""_parse_mysql_url の契約（ローカル / RDS / Cloud SQL）を固定する。"""

from __future__ import annotations

import unittest

from app.db.connection import _parse_mysql_url


class ParseMysqlUrlTests(unittest.TestCase):
    def test_local_tcp(self) -> None:
        got = _parse_mysql_url("mysql://u:p@localhost:3306/mydb")
        self.assertEqual(
            got,
            {
                "host": "localhost",
                "port": 3306,
                "user": "u",
                "password": "p",
                "db": "mydb",
                "unix_socket": None,
            },
        )

    def test_rds_tcp(self) -> None:
        got = _parse_mysql_url(
            "mysql+aiomysql://u:p@db.xxx.ap-northeast-1.rds.amazonaws.com:3306/prod"
        )
        self.assertEqual(got["host"], "db.xxx.ap-northeast-1.rds.amazonaws.com")
        self.assertEqual(got["port"], 3306)
        self.assertEqual(got["db"], "prod")
        self.assertIsNone(got["unix_socket"])

    def test_tcp_default_port(self) -> None:
        got = _parse_mysql_url("mysql://u:p@127.0.0.1/db")
        self.assertEqual(got["port"], 3306)
        self.assertEqual(got["host"], "127.0.0.1")

    def test_cloud_sql_socket_query(self) -> None:
        got = _parse_mysql_url(
            "mysql://mitene:secret@localhost/veho-mitene-mysql-dev"
            "?socket=/cloudsql/proj:asia-northeast1:inst"
        )
        self.assertEqual(got["unix_socket"], "/cloudsql/proj:asia-northeast1:inst")
        self.assertEqual(got["db"], "veho-mitene-mysql-dev")
        self.assertEqual(got["user"], "mitene")
        self.assertEqual(got["password"], "secret")

    def test_local_mysqld_sock(self) -> None:
        got = _parse_mysql_url(
            "mysql://u:p@/mydb?unix_socket=/var/run/mysqld/mysqld.sock"
        )
        self.assertEqual(got["unix_socket"], "/var/run/mysqld/mysqld.sock")
        self.assertEqual(got["db"], "mydb")
        self.assertIsNotNone(got["unix_socket"])

    def test_urlencoded_password(self) -> None:
        got = _parse_mysql_url("mysql://app:q%3Dsecret@10.0.1.5:3306/db")
        self.assertEqual(got["password"], "q=secret")


if __name__ == "__main__":
    unittest.main()
