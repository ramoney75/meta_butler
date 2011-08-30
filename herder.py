import ConfigParser, json, memcache, urllib2, datetime
import lxml.html

class Herder:
  def __init__(self):
    self.config = ConfigParser.ConfigParser()
    self.config.readfp(open("config.txt"))
    self.servers = self.parse_servers_config(self.config.get("herder", "servers"))
    connection_string = self.config.get("herder", "memcache_host") + ":"
    connection_string += self.config.get("herder", "memcache_port")
    self.mc = memcache.Client([connection_string], debug=0)
    

  def parse_servers_config(self, servers_csv):
    return [server.strip() for server in servers_csv.split(',')]
    
  def claim_page_html_to_memcached(self, server, html_string, keys):
    server = self.sanitise_server_address_for_saving(server)
    html = lxml.html.fromstring(html_string)
    rows = html.cssselect("#projectStatus tr")
    for row in rows:
      claimer = self.get_claimer_from_row(row)
      job_name = self.get_job_name_from_row(row)
      
      if claimer is not None and job_name is not None:
        claim_key = str("-*-".join([server, job_name, "claim"]))
        self.mc.set(claim_key, claimer)
        keys.append(claim_key)
        
  
  def get_job_name_from_row(self, row):
    links = row.cssselect("td a")  
    for link in links:
      if not link.text_content().startswith("#") and link.text_content().strip() != "":
        return self.sanitise_job_name_for_saving(link.text_content().strip())
    return None
  
  def get_claimer_from_row(self, row):
    tds = row.cssselect("td")
    for td in tds:
      if td.text_content().startswith("claimed by"):
        return td.text_content().replace("claimed by", "").strip()
    return None
    
  
  def server_json_to_memcached(self, now, server, json_string, keys):
    o = json.loads(json_string)
    for job in o['jobs']:
      server = self.sanitise_server_address_for_saving(server)
      job_name = self.sanitise_job_name_for_saving(job['name'])
      color_key = str("-*-".join([server, job_name, "color"]))
      refresh_time_key = str("-*-".join([server, job_name, "refresh-time"]))
      self.mc.set(color_key, str(job['color']))
      self.mc.set(refresh_time_key, now)
      keys += [color_key, refresh_time_key]
      
      
  def harvest_servers(self):
    full_list_of_keys = []
    for server in self.servers:
      content = self.download_server_info(server)
      now = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
      self.server_json_to_memcached(now, server, content, full_list_of_keys)
      
      claim_content = self.download_claim_info(server)
      self.claim_page_html_to_memcached(server, claim_content, full_list_of_keys)
      
    self.mc.set("full_list_of_keys", full_list_of_keys)
    
    
  @classmethod
  def download_server_info(cls, server):
    try:
      return urllib2.urlopen(Herder.sanitise_server_address_for_request(server) + "api/json").read()
    except Exception, (error):
      print "error downloading jobs info from: " + server
      return '{"jobs":[]}'
  
  @classmethod
  def download_claim_info(cls, server):
    try:
      return urllib2.urlopen(Herder.sanitise_server_address_for_request(server) + "claims/?").read()
    except Exception, (error):
      print "error downloading claims info from: " + server
      return '<table />'
      
    
  @classmethod
  def sanitise_server_address_for_request(cls, address):
    if not address.startswith("http://") and not address.startswith("https://"):
      address = "http://" + address
    if not address.endswith("/"):
      address = address + "/"
    return address
    
  @classmethod
  def sanitise_server_address_for_saving(cls, address):
    return address.replace("https://", "").replace("http://", "").replace("/", "").split(":")[0]
    
  @classmethod
  def sanitise_job_name_for_saving(cls, job):
    return job.replace(" ", "_")
    
if __name__ == '__main__':
  h = Herder()
  h.harvest_servers()