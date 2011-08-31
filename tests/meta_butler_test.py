from nose.tools import *
from mock import patch, Mock
from meta_butler import MetaButler
from unittest import TestCase
import os.path, time

class TestHerding:

  @patch('urllib2.urlopen')
  def test_download_server_info(self, fake_uopen):
    fake_uopen.return_value.read.return_value = "somejson"
    MetaButler.download_server_info("http://someserver/")
    fake_uopen.assert_called_once_with("http://someserver/api/json")
  
  @patch('urllib2.urlopen')
  def test_download_claim_info(self, fake_uopen):
    fake_uopen.return_value.read.return_value = "somehtml"
    MetaButler.download_claim_info("http://someserver/")
    fake_uopen.assert_called_once_with("http://someserver/claims/?")
  
  def test_collect_jobs_from_json(self):
    butler = MetaButler()
    butler.collect_jobs_from_json('http://ci.dev/', '{"jobs":[{"name": "job1", "color": "blue"}]}')
    job = butler.jobs["http://ci.dev/jobs/job1"]
    assert job['name'] == "job1"
    assert job['server'] == "http://ci.dev/"
    assert job['color'] == "blue"
    
  def test_collect_claims_from_html(self):
    butler = MetaButler()
    butler.jobs = {
      "http://ci.dev/jobs/unit_tests": {"name": "unit_tests"}, 
      "http://ci.dev/jobs/acceptance_tests": {"name": "acceptance_tests"}, 
    }
    html_content = """
    <table class="sortable pane bigtable" id="projectStatus">
      <tr>
        <td data="0"><a href="/job/unit_tests/21891/"><img alt="Failed" src="/static/bad8f36c/images/32x32/red.png" /></a></td>
        <td><a href="/job/unit_tests/">unit_tests</a> <a href="/job/unit_tests/21891/">#21891</a></td>
        <td data="2011-08-30T11:05:51Z">41 sec</td>
        <td data="2011-08-19T02:50:26Z">11 days</td>
        <td>claimed by Gob Bluth</td>
        <td></td>
      </tr>
      <tr>
        <td data="0"><a href="/job/acceptance_tests/2669/"><img alt="Failed" src="/static/bad8f36c/images/32x32/red.png" /></a></td>
        <td><a href="/job/acceptance_tests/">acceptance_tests</a> <a href="/job/acceptance_tests/2669/">#2669</a></td>
        <td data="2011-08-29T16:05:46Z">19 hr</td>
        <td data="2011-08-22T16:05:46Z">7 days 19 hr</td>
        <td>claimed by Michael Bluth</td>
        <td></td>
      </tr>
    </table>
    """
    butler.collect_claims_from_html('http://ci.dev/', html_content)
    assert butler.jobs["http://ci.dev/jobs/unit_tests"]['claim'] == "Gob Bluth"
    assert butler.jobs["http://ci.dev/jobs/acceptance_tests"]['claim'] == "Michael Bluth"
    
  def test_save_jobs_to_memcached(self):
    memcache_client_patcher = patch('memcache.Client')
    fake_mc = memcache_client_patcher.start()
    butler = MetaButler()
    butler.jobs = {"yep": "nope"}
    butler.save_jobs()
    fake_mc.return_value.set.assert_called_once_with('meta_butler_jobs', {'yep': 'nope'})
    memcache_client_patcher.stop()
  
  
  @patch("time.strftime")
  def test_add_refresh_time_to_jobs(self, fake_strftime):
    fake_strftime.return_value = "some time"
    butler = MetaButler()
    butler.jobs = {
      "http://ci.dev/jobs/unit_tests": {"name": "unit_tests"}
    }
    butler.add_refresh_time_to_jobs()
    assert butler.jobs["http://ci.dev/jobs/unit_tests"]["refresh"] == "some time"