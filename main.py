""".

CA Servicedesk API
Author: Erik Horton

"""
import requests
from myauth import USERNAME, PASSWORD

HOST = "sm1s.saas.ca.com"
API = "/NimsoftServiceDesk/servicedesk/webservices/"
RESPONSE_FORMAT = "JSON"
HEADERS = {
    "Accept-Encoding": "gzip,deflate",
    "User-Agent": "Python Requests",
    "Content-Type": "text/xml;charset=UTF-8",
}


def get_body(call, settings):
    """Take in parameters and returns a soap envelope."""
    body = """
    <soapenv:Envelope xmlns:soapenv=\
    "http://schemas.xmlsoap.org/soap/envelope/" \
    xmlns:wrap="http://wrappers.webservice.appservices.core.inteqnet.com" \
    xmlns:xsd="http://beans.webservice.appservices.core.inteqnet.com/xsd">
       <soapenv:Header/>
       <soapenv:Body>
          <wrap:{3}>
             <wrap:credentials>
                <xsd:userName>{0}</xsd:userName>
                <xsd:userPassword>{1}</xsd:userPassword>
             </wrap:credentials>
             <wrap:extendedSettings>
                <xsd:responseFormat>{2}</xsd:responseFormat>
             </wrap:extendedSettings>
             {4}
          </wrap:{3}>
       </soapenv:Body>
    </soapenv:Envelope>
    """.format(USERNAME, PASSWORD, RESPONSE_FORMAT, call, settings)

    return body


def servicedesk_call(endpoint, call, settings):
    """Request CA Service Desk API."""
    data = get_body(call, settings)
    url = "https://" + HOST + API + endpoint
    response = requests.post(url, data=data, headers=HEADERS)
    return response.content


def get_incident(incident_number):
    """Get incident details."""
    endpoint = "Incident.IncidentHttpSoap11Endpoint/"
    call = "getIncident"
    settings = "<wrap:ticketIdentifier>{0}</wrap:ticketIdentifier>\
        ".format(incident_number)
    return servicedesk_call(endpoint, call, settings)


def list_service_requests():
    """List Service Requests."""
    endpoint = "ServiceRequest.ServiceRequestHttpSoap11Endpoint/"
    call = "listServiceRequests"
    settings = "<wrap:searchText></wrap:searchText>"
    return servicedesk_call(endpoint, call, settings)

# print get_incident("300-275476")
print list_service_requests()
