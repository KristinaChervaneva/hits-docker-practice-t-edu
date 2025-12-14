import random
from locust import HttpUser, task, between


class ClinicUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def view_main(self):
        self.client.get("/")

    @task(5)
    def view_hospitals(self):
        self.client.get("/hospital")

    @task(3)
    def view_doctors(self):
        self.client.get("/doctor")

    @task(3)
    def view_patients(self):
        self.client.get("/patient")

    @task(2)
    def view_diagnosis(self):
        self.client.get("/diagnosis")

    @task(2)
    def create_hospital(self):
        payload = {
            "name": f"Load Hospital {random.randint(1, 10_000_000)}",
            "address": f"Street {random.randint(1, 1000)}",
            "beds_number": str(random.randint(10, 500)),
            "phone": f"+31{random.randint(100000000, 999999999)}",
        }
        self.client.post("/hospital", data=payload)

    @task(2)
    def create_patient(self):
        payload = {
            "surname": f"Surname{random.randint(1, 10_000_000)}",
            "born_date": "2000-01-01",
            "sex": random.choice(["M", "F"]),
            "mpn": str(random.randint(100000, 999999)),
        }
        self.client.post("/patient", data=payload)
