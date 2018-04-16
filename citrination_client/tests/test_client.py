from citrination_client import *
from os import environ
import os
from json import loads
from pypif.obj.system import System
from pypif.pif import dump
import random
import string
import time
import pytest

def _almost_equal(test_value, reference_value, tolerance=1.0e-9):
    """
    Numerical equality with a tolerance
    """
    return abs(test_value - reference_value) < tolerance

def assert_run_accepted(view_id, run, client):
    status = client.get_design_run_status(view_id, run.uuid)
    assert status.accepted()

def kill_and_assert_killed(view_id, run, client):
    killed_uid = client.kill_design_run(view_id, run.uuid)

    assert killed_uid == run.uuid

    status = client.get_design_run_status(view_id, run.uuid)
    assert status.killed()

class TestClient():

    @classmethod
    def setup_class(cls):
        cls.client = CitrinationClient(environ['CITRINATION_API_KEY'], environ['CITRINATION_SITE'])
        # Append dataset name with random string because one user can't have more than
        # one dataset with the same name
        random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        dataset_name = "Tutorial dataset " + random_string
        cls.set_id = loads(cls.client.create_data_set(name=dataset_name, description="Dataset for tutorial", share=0).content.decode('utf-8'))['id']
        cls.test_file_root = './citrination_client/tests/test_files/'

    def get_test_file_hierarchy_count(self):
        test_dir = self.test_file_root
        return sum([len(files) for r, d, files in os.walk(test_dir)])

    def test_start_client(self):
        assert self.client is not None

    def test_upload_pif(self):
        pif = System()
        pif.id = 0

        with open("tmp.json", "w") as fp:
            dump(pif, fp)
        response = loads(self.client.upload_file("tmp.json", self.set_id))
        assert response["message"] == "Upload is complete."

    def test_file_listing(self):
        src_path = self.test_file_root + "keys_and_values.json"
        dest_path = "test_file_list.json"
        self.client.upload(self.set_id, src_path, dest_path)
        listed_files = self.client.list_files(self.set_id, dest_path)["files"]
        assert len(listed_files) == 1
        assert listed_files[0] == dest_path

    def test_upload_directory(self):
        count_to_add = self.get_test_file_hierarchy_count()
        src_path = self.test_file_root
        dest_path = "test_directory_upload/"
        before_count = self.client.matched_file_count(self.set_id)
        self.client.upload(self.set_id, src_path, dest_path)
        after_count = self.client.matched_file_count(self.set_id)
        assert after_count == (before_count + count_to_add)

    @staticmethod
    def _test_prediction_values(prediction):
        """
        Assertions for the test_predict and test_predict_distribution methods
        """
        egap = '$\\varepsilon$$_{gap}$ ($\\varepsilon$$_{LUMO}$-$\\varepsilon$$_{HOMO}$)'
        voltage = 'Open-circuit voltage (V$_{OC}$)'
        assert 'Mass'  in prediction, "Mass prediction missing (check ML logic)"
        assert egap    in prediction, "E_gap prediction missing (check ML logic)"
        assert voltage in prediction, "V_OC prediction missing (check ML logic)"

        assert _almost_equal(prediction['Mass'][0], 250,  60.0), "Mass mean prediction beyond tolerance (check ML logic)"
        assert _almost_equal(prediction['Mass'][1], 30.0, 40.0), "Mass sigma prediction beyond tolerance (check ML logic)"
        assert _almost_equal(prediction[egap][0], 2.6,  0.7), "E_gap mean prediction beyond tolerance (check ML logic)"
        assert _almost_equal(prediction[egap][1], 0.50, 0.55), "E_gap sigma prediction beyond tolerance (check ML logic)"
        assert _almost_equal(prediction[voltage][0], 1.0, 0.9), "V_OC mean prediction beyond tolerance (check ML logic)"
        assert _almost_equal(prediction[voltage][1], 0.8, 0.9), "V_OC sigma prediction beyond tolerance (check ML logic)"

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://citrination.com", reason="Predict test only supported on public")
    def test_predict(self):
        """
        Test predictions on the standard organic model

        This model is trained on HCEP data.  The prediction mirrors that on the
        organics demo script
        """

        client = CitrinationClient(environ['CITRINATION_API_KEY'], environ['CITRINATION_SITE'])
        inputs = [{"SMILES": "c1(C=O)cc(OC)c(O)cc1"}, ]
        vid = "177"

        resp = client.predict(vid, inputs, method="scalar")
        prediction = resp['candidates'][0]
        self._test_prediction_values(prediction)

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://citrination.com", reason="Predict from distribution test only supported on public")
    def test_predict_from_distribution(self):
        """
        Test predictions on the standard organic model

        Same as `test_predict` but using the `from_distribution` method
        """

        client = CitrinationClient(environ['CITRINATION_API_KEY'], environ['CITRINATION_SITE'])
        inputs = [{"SMILES": "c1(C=O)cc(OC)c(O)cc1"}, ]
        vid = "177"

        resp = client.predict(vid, inputs, method="from_distribution")
        prediction = resp['candidates'][0]
        self._test_prediction_values(prediction)

    @pytest.mark.skip(reason="this template is no longer accessible (404)")
    def test_predict_custom(self):
        client = CitrinationClient(environ['CITRINATION_API_KEY'], environ['CITRINATION_SITE'])
        input = {"canary_x": "0.5", "temperature": "100", "canary_y": "0.75"}
        resp = client.predict_custom("canary", input)
        prediction = resp['candidates'][0]
        assert 'canary_zz' in prediction.keys()
        assert 'canary_z' in prediction.keys()

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://citrination.com", reason="TSNE test only supported on public")
    def test_tsne(self):
        """
        Test that we can grab the t-SNE from a pre-trained view
        """
        client = CitrinationClient(environ['CITRINATION_API_KEY'], environ['CITRINATION_SITE'])
        resp = client.tsne("1623")

        assert len(resp) == 1, "Expected a single tSNE block but got {}".format(len(resp))

        tsne_y = resp[list(resp.keys())[0]]
        assert "x" in tsne_y, "Couldn't find x component of tsne projection"
        assert "y" in tsne_y, "Couldn't find y component of tsne projection"
        assert "z" in tsne_y, "Couldn't find property label for tsne projection"
        assert "uid" in tsne_y, "Couldn't find uid in tsne projection"
        assert "label" in tsne_y, "Couldn't find label in tsne projection"

        assert len(tsne_y["x"]) == len(tsne_y["y"]),     "tSNE components x and y had different lengths"
        assert len(tsne_y["x"]) == len(tsne_y["z"]),     "tSNE components x and z had different lengths"
        assert len(tsne_y["x"]) == len(tsne_y["label"]), "tSNE components x and uid had different lengths"
        assert len(tsne_y["x"]) == len(tsne_y["uid"]),   "tSNE components x and label had different lengths"

    def _trigger_run(self, client, view_id, num_candidates=10, effort=1, constraints=[], target=Target(name="Property Band gap", objective="Max")):

        return client.submit_design_run(data_view_id=view_id,
                                         num_candidates=num_candidates,
                                         constraints=constraints,
                                         target=target,
                                         effort=effort)

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://qa.citrination.com", reason="Design tests only supported on qa")
    def test_experimental_design(self):
        """
        Tests that a design run can be triggered, the status can be polled, and once it is finished, the results can be retrieved.
        """
        client = CitrinationClient(environ["CITRINATION_API_KEY"], environ["CITRINATION_SITE"])
        view_id = "138"
        run = self._trigger_run(client, view_id, constraints=[CategoricalConstraint(name="Property Color",
                                                 accepted_categories=["Gray"])])

        try:
            status = client.get_design_run_status(view_id, run.uuid)
            while not status.finished():
                time.sleep(1)
                status = client.get_design_run_status(view_id, run.uuid)
        except Exception:
            client.kill_design_run(view_id, run.uuid)
            raise

        results = client.get_design_run_results(view_id, run.uuid)
        assert len(results.next_experiments) > 0
        assert len(results.best_materials) > 0

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://qa.citrination.com", reason="Design tests only supported on qa")
    def test_design_run_effort_limit(self):
        """
        Tests that a design run cannot be submitted with an effort
        value greater than 30
        """
        client = CitrinationClient(environ["CITRINATION_API_KEY"], environ["CITRINATION_SITE"])
        view_id = "138"

        try:
            run = self._trigger_run(client, view_id, effort=1000)
            assert False
        except CitrinationClientError:
            assert True

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://qa.citrination.com", reason="Design tests only supported on qa")
    def test_kill_experimental_desing(self):
        """
        Tests that an in progress design run can be killed and the status
        will be reported as killed afterward.
        """
        client = CitrinationClient(environ["CITRINATION_API_KEY"], environ["CITRINATION_SITE"])
        view_id = "138"
        run = self._trigger_run(client, view_id)
        assert_run_accepted(view_id, run, client)
        kill_and_assert_killed(view_id, run, client)

    @pytest.mark.skipif(environ['CITRINATION_SITE'] != "https://qa.citrination.com", reason="Design tests only supported on qa")
    def test_can_submit_run_with_no_target(self):
        """
        Tests that a design run can be submitted successfully with no target.
        """
        client = CitrinationClient(environ["CITRINATION_API_KEY"], environ["CITRINATION_SITE"])
        view_id = "138"

        run = self._trigger_run(client, view_id, target=None)

        assert_run_accepted(view_id, run, client)
        kill_and_assert_killed(view_id, run, client)