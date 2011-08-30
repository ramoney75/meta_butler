from nose.tools import *
from mock import patch, Mock
from herder import Herder
from unittest import TestCase
import os.path

class TestHerding:

  def setup(self):
    self.memcache_client_patcher = patch('memcache.Client')
    self.fake_mc = self.memcache_client_patcher.start()
    
  def teardown(self):
    self.memcache_client_patcher.stop()
  
  def test_sanitise_server_address_for_request(self):
    assert Herder.sanitise_server_address_for_request("something") == 'http://something/'
    assert Herder.sanitise_server_address_for_request("https://something") == 'https://something/'
    
  def test_sanistise_server_address_for_saving(self):
    assert Herder.sanitise_server_address_for_saving("something") == 'something'
    assert Herder.sanitise_server_address_for_saving("https://something:8080") == 'something'
  
  def test_sanitise_job_name_for_saving(self):
    assert Herder.sanitise_job_name_for_saving("something blue") == 'something_blue'
    
  @patch('urllib2.urlopen')
  def test_download_server_info(self, fake_uopen):
    fake_uopen.return_value.read.return_value = "somejson"
    assert Herder.download_server_info("someserver") == "somejson"
    fake_uopen.assert_called_once_with("http://someserver/api/json")
  
  def test_server_json_to_memcached(self):
    herder = Herder()
    now = '20110830 12:34:56'
    herder.server_json_to_memcached(now, 'ci.dev', '{"jobs":[{"name": "job1", "color": "blue"}]}', [])
    
    assert self.fake_mc.return_value.method_calls[0][0] == "set"
    assert self.fake_mc.return_value.method_calls[0][1] == ('ci.dev-*-job1-*-color', 'blue')
    assert self.fake_mc.return_value.method_calls[1][0] == "set"
    assert self.fake_mc.return_value.method_calls[1][1] == ('ci.dev-*-job1-*-refresh-time', now)
    
  def test_claim_page_html_to_memcached(self):
    
    herder = Herder()
    
    f = open(os.path.join("tests", "claim_page_fixture.txt"))
    html = f.read()
    f.close()
    
    herder.claim_page_html_to_memcached('ci.dev', html, [])
    assert self.fake_mc.return_value.method_calls[0][0] == "set"
    assert self.fake_mc.return_value.method_calls[0][1] == ('ci.dev-*-Offmarket-*-claim', 'Bertrand')
  
  # end 2 end(ish) test
  @patch('ConfigParser.ConfigParser')
  def test_harverst(self, fake_config):
    fake_config.return_value.get.return_value = "http://ci.dev:8080"
    
    dlsi_patcher = patch('herder.Herder.download_server_info')
    fake_dlsi = dlsi_patcher.start()
    fake_dlsi.return_value = '{"jobs":[{"name": "job1", "color": "blue"}, {"name": "job2", "color": "disabled"}]}'
    
    dlc_patcher = patch('herder.Herder.download_claim_info')
    fake_dlc = dlc_patcher.start()
    fake_dlc.return_value = '<table />'

    herder = Herder()
    herder.harvest_servers()
    
    assert self.fake_mc.return_value.method_calls[0][0] == "set"
    assert self.fake_mc.return_value.method_calls[0][1] == ('ci.dev-*-job1-*-color', 'blue')
    assert self.fake_mc.return_value.method_calls[1][0] == "set"
    assert self.fake_mc.return_value.method_calls[1][1][0] == 'ci.dev-*-job1-*-refresh-time'
    assert self.fake_mc.return_value.method_calls[2][0] == "set"
    assert self.fake_mc.return_value.method_calls[2][1] == ('ci.dev-*-job2-*-color', 'disabled')
    assert self.fake_mc.return_value.method_calls[3][0] == "set"
    assert self.fake_mc.return_value.method_calls[3][1][0] == 'ci.dev-*-job2-*-refresh-time'
    
    dlsi_patcher.stop()