#!/usr/bin/env python3

import configparser
import requests
import json
from datetime import datetime
import os
import urllib
import xml.etree.ElementTree
import re

print(datetime.now().isoformat() + " ### start tomtom2runtastic ###")
print(datetime.now().isoformat() + " --- load configuration ---")
#parse configuration file
script_dir = os.path.dirname(os.path.realpath(__file__))
conf_file = configparser.ConfigParser()
conf_file.readfp(open(script_dir + "/tomtom2runtastic.ini"))

GPX_CACHE = conf_file.get("common", "gpxcache")

TOMTOM_EMAIL = conf_file.get("tomtom", "email")
TOMTOM_PASSWORD = conf_file.get("tomtom", "password")

RUNTASTIC_EMAIL = conf_file.get("runtastic", "email")
RUNTASTIC_PASSWORD = conf_file.get("runtastic", "password")

print(datetime.now().isoformat() +" --- start tomtom activtiy download ---")
#login to tomtom
tomtom_session = requests.Session()
tomtom_login_data = {"email":TOMTOM_EMAIL, "password":TOMTOM_PASSWORD}
tomtom_headers = {"content-type": "application/json;charset=UTF-8"}

print(datetime.now().isoformat() + " - login to tomtom")
tomtom_login_response = tomtom_session.post("https://mysports.tomtom.com/service/webapi/v2/auth/user/login", data=json.dumps(tomtom_login_data), headers=tomtom_headers)
print(datetime.now().isoformat() + " - tomtom login status code: " + str(tomtom_login_response.status_code))

#request tomtom activity list
print(datetime.now().isoformat() + " - request tomtom activity list")
tomtom_activity_response = tomtom_session.get("https://mysports.tomtom.com/service/webapi/v2/activity/")
print(datetime.now().isoformat() + " - tomtom activity list status code: " + str(tomtom_activity_response.status_code))

#parse response for running activities
print(datetime.now().isoformat() + " - gpx file download:")
tomtom_activity_json = tomtom_activity_response.json()
for tomtom_workouts in tomtom_activity_json["workouts"]:
    if tomtom_workouts["cohorts"][0]["cohort"] == "Running":
	#generate timestamp and url for gpx file
        tomtom_workouts_startdatetime = tomtom_workouts["start_datetime_user"]
        tomtom_workouts_startdatetime = datetime.strptime(tomtom_workouts_startdatetime[:19],"%Y-%m-%dT%H:%M:%S")
        tomtom_gpx_url = "https://mysports.tomtom.com/service/webapi/v2/activity/" + str(tomtom_workouts["id"]) + "?dv=1.5&format=gpx"
        tomtom_gpx_filename = "run-" + tomtom_workouts_startdatetime.strftime("%Y%m%dT%H%M%S") + ".gpx"
	#download gpx file if not in cache
        if os.path.exists(GPX_CACHE+tomtom_gpx_filename):
            print(datetime.now().isoformat() + " - workout id: " + str(tomtom_workouts["id"]) + "; gpx file: " + tomtom_gpx_filename + " - skiped")
        else:
            tomtom_gpx_response = tomtom_session.get(tomtom_gpx_url)
            open(GPX_CACHE+tomtom_gpx_filename, 'wb').write(tomtom_gpx_response.content)
            print(datetime.now().isoformat() + " - workout id: " + str(tomtom_workouts["id"]) + "; gpx file: " + tomtom_gpx_filename + " - saved")

print(datetime.now().isoformat() + " --- tomtom activity download completed ---")


print(datetime.now().isoformat() + " --- load gpx file list---")
#load gpx upload list for runtastic		
runtastic_gpx_upload_list = os.listdir(GPX_CACHE)

print(datetime.now().isoformat() + " --- start runtastic activtiy upload ---")
#login to runtastic
runtastic_headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
runtastic_login_data = urllib.parse.urlencode({"user[email]": RUNTASTIC_EMAIL,
					       "user[password]": RUNTASTIC_PASSWORD,
                                               "authenticity_token": ""})

print(datetime.now().isoformat() + " - login to runtastic")
runtastic_login_response = requests.post("https://www.runtastic.com/en/d/users/sign_in.json", data=runtastic_login_data, headers=runtastic_headers)
print(datetime.now().isoformat() + " - runtastic login status code: " + str(runtastic_login_response.status_code))

#parse runtastic authentication data
runtastic_login_json = runtastic_login_response.json()
runtastic_login_xml = xml.etree.ElementTree.fromstring(runtastic_login_json['update'].replace("last_name}}}'>", "last_name}}}' />"))

runtastic_username = runtastic_login_json['current_user']['slug']
runtastic_uid = runtastic_login_json['current_user']['id']
runtastic_token = (runtastic_login_xml.findall("./*/*/*/*/*/*/*/*[@method='post']/*/input[@name='authenticity_token']"))[0].get('value')
runtastic_cookie = dict(runtastic_login_response.cookies)

#request runtastic activity list
print(datetime.now().isoformat() + " - request runtastic activity list")
runtastic_activity_response = requests.get("https://www.runtastic.com/en/users/" + runtastic_username + "/sport-sessions", headers=runtastic_headers, cookies=runtastic_cookie)
print(datetime.now().isoformat() + " - runtastic activity list status code: " + str(runtastic_activity_response.status_code))

runtastic_activities_keys = re.search("var index_data = (.*);", runtastic_activity_response.text).group()
runtastic_activities_keys = re.search("\[\[.*\]\]", runtastic_activities_keys).group()
runtastic_activities_keys = json.loads(runtastic_activities_keys)
runtastic_activities_keys_str =  ",".join(str(runtastic_activity_key[0]) for runtastic_activity_key in runtastic_activities_keys)

runtastic_activities_data = urllib.parse.urlencode({"user_id": runtastic_uid,
						    "authenticity_token": runtastic_token,
						    "items": runtastic_activities_keys_str})

print(datetime.now().isoformat() + " - request runtastic activities details")													
runtastic_activities_detail_response = requests.post("https://www.runtastic.com/api/run_sessions/json", data=runtastic_activities_data, headers=runtastic_headers, cookies=runtastic_cookie)
print(datetime.now().isoformat() + " - runtastic activities details status code: " + str(runtastic_activities_detail_response.status_code))

#parse response for activites
print(datetime.now().isoformat() + " - compare file lists:")
runtastic_activities_detail_json = runtastic_activities_detail_response.json()
for runtastic_activity in runtastic_activities_detail_json:
    #generate timestamp for gpx file
    runtastic_activity_startdatetime = datetime(int(runtastic_activity["date"]["year"]),
                                                int(runtastic_activity["date"]["month"]),
                                                int(runtastic_activity["date"]["day"]),
                                                int(runtastic_activity["date"]["hour"]),
                                                int(runtastic_activity["date"]["minutes"]),
                                                int(runtastic_activity["date"]["seconds"]))
    runtastic_gpx_file = "run-" + runtastic_activity_startdatetime.strftime("%Y%m%dT%H%M%S") + ".gpx"
    #remove known gpx files from upload list
    if runtastic_gpx_file in runtastic_gpx_upload_list:
        print(datetime.now().isoformat() + " - gpx file: " + runtastic_gpx_file + " - exist")
        runtastic_gpx_upload_list.remove(runtastic_gpx_file)
		
#upload unknown gpx files to runtastic
print(datetime.now().isoformat() + " - gpx file upload:")
for runtastic_gpx_file in runtastic_gpx_upload_list:
    runtastic_upload_headers = {"Content-Type": "application/octet-stream",
				"Accept": "*/*",
				"X-File-Name": runtastic_gpx_file,
				"X-Requested-With": "XMLHttpRequest"}
    runtastic_upload_data = open(GPX_CACHE + runtastic_gpx_file, "rb").read()
    runtastic_upload_response = requests.post("https://www.runtastic.com/import/upload_session?authenticity_token=" + runtastic_token + "&qqfile=" + runtastic_gpx_file, data=runtastic_upload_data, headers=runtastic_upload_headers , cookies=runtastic_cookie)
    print(datetime.now().isoformat() + " - gpx file: " + runtastic_gpx_file + " - uploaded")

print(datetime.now().isoformat() + " --- runtastic activtiy upload completed ---")
print(datetime.now().isoformat() + " ### tomtom2runtastic completed ###")
