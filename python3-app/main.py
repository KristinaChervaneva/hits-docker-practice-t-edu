#!/usr/bin/env python3
import logging
import os
import sys

import redis
import tornado.ioloop
import tornado.web
from tornado.options import parse_command_line

PORT = 8888

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

# Redis client (same behavior as before)
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Redis key helpers (keep the same keys as in original code)
def _autoid_key(entity: str) -> str:
    return f"{entity}:autoID"


def _entity_key(entity: str, entity_id: str | int) -> str:
    return f"{entity}:{entity_id}"


def _doctor_patient_key(doctor_id: str | int) -> str:
    return f"doctor-patient:{doctor_id}"


class BaseHandler(tornado.web.RequestHandler):
    """Common helpers for handlers to reduce duplication."""

    def _redis_refused(self) -> None:
        # Keep original behavior: 400 + message
        self.set_status(400)
        self.write("Redis connection refused")

    def _fetch_hash_items(self, entity: str) -> list[dict]:
        """
        Fetch all existing hashes for entity IDs from 0..autoID-1.
        Keeps original behavior:
          - uses <entity>:autoID
          - stores records in list without decoding keys/values
        """
        items: list[dict] = []

        raw_auto_id = r.get(_autoid_key(entity))
        # In original code .decode() would crash if key absent; keep app stable instead.
        # If autoID is missing, treat as 0 items.
        if not raw_auto_id:
            return items

        try:
            auto_id = int(raw_auto_id.decode())
        except (ValueError, AttributeError):
            # If something weird is stored, treat as empty (safer than crashing)
            return items

        for i in range(auto_id):
            result = r.hgetall(_entity_key(entity, i))
            if result:
                items.append(result)

        return items


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html")


class HospitalHandler(BaseHandler):
    def get(self):
        try:
            items = self._fetch_hash_items("hospital")
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.render("templates/hospital.html", items=items)

    def post(self):
        name = self.get_argument("name")
        address = self.get_argument("address")
        beds_number = self.get_argument("beds_number")
        phone = self.get_argument("phone")

        if not name or not address:
            self.set_status(400)
            self.write("Hospital name and address required")
            return

        logging.debug(
            "Create hospital: name=%s address=%s beds_number=%s phone=%s",
            name,
            address,
            beds_number,
            phone,
        )

        try:
            raw_id = r.get(_autoid_key("hospital"))
            hospital_id = raw_id.decode() if raw_id else "0"

            write_count = 0
            write_count += r.hset(_entity_key("hospital", hospital_id), "name", name)
            write_count += r.hset(_entity_key("hospital", hospital_id), "address", address)
            write_count += r.hset(_entity_key("hospital", hospital_id), "phone", phone)
            write_count += r.hset(
                _entity_key("hospital", hospital_id), "beds_number", beds_number
            )

            r.incr(_autoid_key("hospital"))
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            # Keep original semantics: expect 4 successful hset results
            if write_count != 4:
                self.set_status(500)
                self.write("Something went terribly wrong")
            else:
                self.write(f"OK: ID {hospital_id} for {name}")


class DoctorHandler(BaseHandler):
    def get(self):
        try:
            items = self._fetch_hash_items("doctor")
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.render("templates/doctor.html", items=items)

    def post(self):
        surname = self.get_argument("surname")
        profession = self.get_argument("profession")
        hospital_ID = self.get_argument("hospital_ID")  # keep param name as in form

        if not surname or not profession:
            self.set_status(400)
            self.write("Surname and profession required")
            return

        logging.debug("Create doctor: surname=%s profession=%s hospital_ID=%s", surname, profession, hospital_ID)

        try:
            raw_id = r.get(_autoid_key("doctor"))
            doctor_id = raw_id.decode() if raw_id else "0"

            if hospital_ID:
                hospital = r.hgetall(_entity_key("hospital", hospital_ID))
                if not hospital:
                    self.set_status(400)
                    self.write("No hospital with such ID")
                    return

            write_count = 0
            write_count += r.hset(_entity_key("doctor", doctor_id), "surname", surname)
            write_count += r.hset(_entity_key("doctor", doctor_id), "profession", profession)
            write_count += r.hset(_entity_key("doctor", doctor_id), "hospital_ID", hospital_ID)

            r.incr(_autoid_key("doctor"))
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            if write_count != 3:
                self.set_status(500)
                self.write("Something went terribly wrong")
            else:
                self.write(f"OK: ID {doctor_id} for {surname}")


class PatientHandler(BaseHandler):
    def get(self):
        try:
            items = self._fetch_hash_items("patient")
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.render("templates/patient.html", items=items)

    def post(self):
        surname = self.get_argument("surname")
        born_date = self.get_argument("born_date")
        sex = self.get_argument("sex")
        mpn = self.get_argument("mpn")

        if not surname or not born_date or not sex or not mpn:
            self.set_status(400)
            self.write("All fields required")
            return

        if sex not in ["M", "F"]:
            self.set_status(400)
            self.write("Sex must be 'M' or 'F'")
            return

        logging.debug("Create patient: surname=%s born_date=%s sex=%s mpn=%s", surname, born_date, sex, mpn)

        try:
            raw_id = r.get(_autoid_key("patient"))
            patient_id = raw_id.decode() if raw_id else "0"

            write_count = 0
            write_count += r.hset(_entity_key("patient", patient_id), "surname", surname)
            write_count += r.hset(_entity_key("patient", patient_id), "born_date", born_date)
            write_count += r.hset(_entity_key("patient", patient_id), "sex", sex)
            write_count += r.hset(_entity_key("patient", patient_id), "mpn", mpn)

            r.incr(_autoid_key("patient"))
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            if write_count != 4:
                self.set_status(500)
                self.write("Something went terribly wrong")
            else:
                self.write(f"OK: ID {patient_id} for {surname}")


class DiagnosisHandler(BaseHandler):
    def get(self):
        try:
            items = self._fetch_hash_items("diagnosis")
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.render("templates/diagnosis.html", items=items)

    def post(self):
        patient_ID = self.get_argument("patient_ID")
        diagnosis_type = self.get_argument("type")
        information = self.get_argument("information")

        if not patient_ID or not diagnosis_type:
            self.set_status(400)
            self.write("Patiend ID and diagnosis type required")
            return

        logging.debug(
            "Create diagnosis: patient_ID=%s type=%s information=%s",
            patient_ID,
            diagnosis_type,
            information,
        )

        try:
            raw_id = r.get(_autoid_key("diagnosis"))
            diagnosis_id = raw_id.decode() if raw_id else "0"

            patient = r.hgetall(_entity_key("patient", patient_ID))
            if not patient:
                self.set_status(400)
                self.write("No patient with such ID")
                return

            write_count = 0
            write_count += r.hset(_entity_key("diagnosis", diagnosis_id), "patient_ID", patient_ID)
            write_count += r.hset(_entity_key("diagnosis", diagnosis_id), "type", diagnosis_type)
            write_count += r.hset(_entity_key("diagnosis", diagnosis_id), "information", information)

            r.incr(_autoid_key("diagnosis"))
        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            if write_count != 3:
                self.set_status(500)
                self.write("Something went terribly wrong")
            else:
                # Keep original message semantics (patient surname is stored as bytes)
                patient_surname = patient.get(b"surname", b"").decode()
                self.write(f"OK: ID {diagnosis_id} for patient {patient_surname}")


class DoctorPatientHandler(BaseHandler):
    def get(self):
        items: dict[int, set[bytes]] = {}
        try:
            raw_auto_id = r.get(_autoid_key("doctor"))
            if raw_auto_id:
                auto_id = int(raw_auto_id.decode())
            else:
                auto_id = 0

            for i in range(auto_id):
                result = r.smembers(_doctor_patient_key(i))
                if result:
                    items[i] = result

        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.render("templates/doctor-patient.html", items=items)

    def post(self):
        doctor_ID = self.get_argument("doctor_ID")
        patient_ID = self.get_argument("patient_ID")

        if not doctor_ID or not patient_ID:
            self.set_status(400)
            self.write("ID required")
            return

        logging.debug("Link doctor-patient: doctor_ID=%s patient_ID=%s", doctor_ID, patient_ID)

        try:
            patient = r.hgetall(_entity_key("patient", patient_ID))
            doctor = r.hgetall(_entity_key("doctor", doctor_ID))

            if not patient or not doctor:
                self.set_status(400)
                self.write("No such ID for doctor or patient")
                return

            r.sadd(_doctor_patient_key(doctor_ID), patient_ID)

        except redis.exceptions.ConnectionError:
            self._redis_refused()
        else:
            self.write(f"OK: doctor ID: {doctor_ID}, patient ID: {patient_ID}")


def init_db() -> None:
    """
    Initialize Redis keys if DB not initiated.
    Keeps original key names and values.
    """
    try:
        db_initiated = r.get("db_initiated")
        if not db_initiated:
            r.set(_autoid_key("hospital"), 1)
            r.set(_autoid_key("doctor"), 1)
            r.set(_autoid_key("patient"), 1)
            r.set(_autoid_key("diagnosis"), 1)
            r.set("db_initiated", 1)
    except redis.exceptions.ConnectionError:
        # Make startup error clearer than a long traceback
        logging.error("Redis connection refused. Please start Redis and retry (REDIS_HOST=%s REDIS_PORT=%s).", REDIS_HOST, REDIS_PORT)
        sys.exit(1)


def make_app() -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static/"}),
            (r"/hospital", HospitalHandler),
            (r"/doctor", DoctorHandler),
            (r"/patient", PatientHandler),
            (r"/diagnosis", DiagnosisHandler),
            (r"/doctor-patient", DoctorPatientHandler),
        ],
        autoreload=True,
        debug=True,
        compiled_template_cache=False,
        serve_traceback=True,
    )


if __name__ == "__main__":
    parse_command_line()
    init_db()
    app = make_app()
    app.listen(PORT)
    logging.info("Listening on %s", PORT)
    tornado.ioloop.IOLoop.current().start()
