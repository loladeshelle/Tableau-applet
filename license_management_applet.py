import json
import requests
import sys
import getpass
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date

days = timedelta(days=60)
new_date = date.today() - days

url = ''
servicenow_user = ''
pwd = ''


XMLNS = {'t': ''}

if sys.version[0] == '3': raw_input=input

class ApiCallError(Exception):
    """ ApiCallError """
    pass

class UserDefinedFieldError(Exception):
    """ UserDefinedFieldError """
    pass

def _encode_for_display(text):
     return text.encode('ascii', errors="backslashreplace").decode('utf-8')


def _check_status(server_response, success_code):
     if server_response.status_code != success_code:
        parsed_response = ET.fromstring(server_response.text)
        error_element = parsed_response.find('t:error', namespaces=XMLNS)
        summary_element = parsed_response.find('.//t:summary', namespaces=XMLNS)
        detail_element = parsed_response.find('.//t:detail', namespaces=XMLNS)

        code = error_element.get('code', 'unknown') if error_element is not None else 'unknown code'
        summary = summary_element.text if summary_element is not None else 'unknown summary'
        detail = detail_element.text if detail_element is not None else 'unknown detail'
        error_message = '{0}: {1} - {2}'.format(code, summary, detail)
        raise ApiCallError(error_message)
     return

def sign_in(server, tokenName, personalAccessTokenSecret,site,):
    url = server + "/api/3.7/auth/signin"
    xml_request = ET.Element('tsRequest')
    credentials_element = ET.SubElement(xml_request, 'credentials', personalAccessTokenName=tokenName, personalAccessTokenSecret=personalAccessTokenSecret)
    ET.SubElement(credentials_element, 'site', contentUrl=site)
    xml_request = ET.tostring(xml_request)

    server_response = requests.post(url, data=xml_request)
    _check_status(server_response, 200)

    server_response = _encode_for_display(server_response.text)
    parsed_response = ET.fromstring(server_response)

    token = parsed_response.find('t:credentials', namespaces=XMLNS).get('token')
    site_id = parsed_response.find('.//t:site', namespaces=XMLNS).get('id')
    return token, site_id

def sign_out(server, auth_token):
    url = server + "/api/3.7/auth/signout"
    server_response = requests.post(url, headers={'x-tableau-auth': auth_token})
    _check_status(server_response, 204)
    return

def query_inactive_users(server, auth_token,site_id, inactive_days, VERSION=3.7):
    url = server + "/api/3.7/sites/{0}//users?filter=lastLogin:lte:{1},siteRole:eq:Creator&fields=name,fullName".format(site_id, inactive_days)
    server_response = requests.get(url, headers={'x-tableau-auth': auth_token})
    _check_status(server_response, 200)

    xml_response = ET.fromstring(_encode_for_display(server_response.text))
    users = xml_response.findall('.//t:user', namespaces=XMLNS)
    return users
    
def create_snow_ticket(url, servicenow_user, pwd, e_number, caller_id):
    data_input= {
    "sysparm_quantity": 1,
    "variables": {
    "dr_a_caller_id": caller_id,
    "dr_a_access_env": "Don't Know",
    "dr_a_req_number":e_number,
    "dr_a_req_access":"Tableau",
    "dr_a_purpose":"Change licence type",
     "dr_a_tlicensetype":"Viewer",
    "project_id":"Technology, Innovation & Engineering (TIE)",
    "project_id_behalf":"Technology, Innovation & Engineering (TIE)",
    "dr_a_access_desc":"Please downgrade " + caller_id + " from Creator to Viewer",
    "dr_a_manager":"N/A",
    "dr_a_contacts":"oshelle@atb.com",
    "dr_a_add_inf":"@IAM - Please remove " + e_number + " - " + caller_id + " from CREATOR and add to VIEWER AD group",
    "tech_gurus_needed":"No",
    "tech_ninjas_needed":"Yes"
    }}

    headers = {"Content-type": "application/json", "Accept":"application/json"}
    data = json.dumps(data_input)
    response = requests.post(url, auth=(servicenow_user, pwd), headers=headers, data=data)
    if response.status_code != 200: 
     print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
     exit()

    server_response = response.json()

def remove_user_list(eNumber, fullName): 
    friendly_name = fullName.split(", ")
    if len(friendly_name) < 2:
        caller_id = friendly_name[0]
    else:
        caller_id = friendly_name[1] + " " + friendly_name[0]
        print(caller_id)
    create_snow_ticket(url=url, servicenow_user=servicenow_user, pwd=pwd, caller_id=caller_id, e_number=eNumber)  

def main():
    server = ""
    tokenName = "accesstoken"
    personalAccessTokenSecret = ""
    site_id = ""
    inactive_days = "{0}T00:00:00Z".format(new_date)
    page_size = 100


    if len(sys.argv) > 1:
        server = sys.argv[1]
        tokenName = sys.argv[2]

    if server == "":
        server = raw_input("\nServer : ")
    
    if tokenName == "":
        tokenName = raw_input("\ntokenName: ")

    if personalAccessTokenSecret == "":
        personalAccessTokenSecret = getpass.getpass("personalAccessTokenSecret: ")
    
    if site_id == "Default":
        site_id = ""
    
    if page_size == "":
        page_size = int(raw_input("\nPage size: "))
    
    print("\nSigning in to obtain authentication token")
    auth_token, site_id = sign_in(server, tokenName, personalAccessTokenSecret, site_id)

    total_available = 0
    total_returned = 0
    done = False

    while not done:
        users = query_inactive_users(server, auth_token, site_id, inactive_days)
    
        for user in users:
            fullName = user.get('fullName') 
            eNumber= user.get('name')
    
            remove_user_list(eNumber, fullName)
        total_returned = total_returned + page_size

        if total_returned >= total_available:
           done = True
    print("\nSigning out and invalidating the authentication token")
    sign_out(server, auth_token)

 
if __name__ == "__main__":
    main()       
    



