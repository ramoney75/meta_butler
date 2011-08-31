import ConfigParser, json, memcache, urllib2, datetime
import lxml.html

class MetaButler:
  def __init__(self):
    self.config = ConfigParser.ConfigParser()
    self.config.readfp(open("config.txt"))
    self.servers = self.parse_servers_config(self.config.get("herder", "servers"))
    connection_string = self.config.get("herder", "memcache_host") + ":"
    connection_string += self.config.get("herder", "memcache_port")
    self.mc = memcache.Client([connection_string], debug=0)
    self.jobs = {}
    

  def parse_servers_config(self, servers_csv):
    return [server.strip() for server in servers_csv.split(',')]
    
  def collect_claims_from_html(self, server, html_string):
    html = lxml.html.fromstring(html_string)
    rows = html.cssselect("#projectStatus tr")
    for row in rows:
      claimer = self.get_claimer_from_row(row)
      job_name = self.get_job_name_from_row(row)
      
      if claimer is not None and job_name is not None:
        if self.jobs[server + "::::" + job_name] is not None:
          self.jobs[server + "::::" + job_name]['claim'] = claimer
        
  
  def get_job_name_from_row(self, row):
    links = row.cssselect("td a")  
    for link in links:
      if not link.text_content().startswith("#") and link.text_content().strip() != "":
        return link.text_content().strip()
    return None
  
  def get_claimer_from_row(self, row):
    tds = row.cssselect("td")
    for td in tds:
      if td.text_content().startswith("claimed by"):
        return td.text_content().replace("claimed by", "").strip()
    return None
      
  def collect_jobs_from_json(self, server, json_string):
    o = json.loads(json_string)
    for job in o['jobs']:
      id = server + "::::" + job['name']
      job_hash = {"name" : job['name'], "url": server + "jobs/" + job['name'], "server" : server, "color" : job['color']}
      self.jobs[id] = job_hash
  
  def save_jobs(self):
    self.mc.set("meta_butler_jobs", self.jobs)
    
  def add_refresh_time_to_jobs(self):
    now = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
    for job in self.jobs.itervalues():
      job['refresh'] = now
      
  def do_your_job(self):
    for server in self.servers:
      jobs_content = self.download_server_info(server)
      self.collect_jobs_from_json(server, jobs_content)
      
      claims_content = self.download_claim_info(server)
      self.collect_claims_from_html(server, claims_content)
      
      self.add_refresh_time_to_jobs()
      self.save_jobs()
    
    
  @classmethod
  def download_server_info(cls, server):
    try:
      return urllib2.urlopen(server + "api/json").read()
    except Exception, (error):
      print "error downloading jobs info from: " + server
      return None
  
  @classmethod
  def download_claim_info(cls, server):
    try:
      return urllib2.urlopen(server + "claims/?").read()
    except Exception, (error):
      print "error downloading claims info from: " + server
      return None
    
if __name__ == '__main__':
  butler = MetaButler()
  butler.do_your_job()