""".

CA Servicedesk API
Author: Erik Horton

"""
import re
import json
import pickle
import requests
from dateutil import parser
from datetime import datetime
from myauth import USERNAME, PASSWORD, GROUP

HOST = "sm1.saas.ca.com"
API = "/NimsoftServiceDesk/servicedesk/webservices/"
RESPONSE_FORMAT = "JSON"
HEADERS = {
    "Accept-Encoding": "gzip,deflate",
    "User-Agent": "Python Requests",
    "Content-Type": "text/xml;charset=UTF-8",
}

ENCODED_FILE = "pickle.dat"


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


def get_incident(ticket_id):
    """Get incident details."""
    endpoint = "Incident.IncidentHttpSoap11Endpoint/"
    call = "getIncident"
    settings = "<wrap:ticketIdentifier>{0}</wrap:ticketIdentifier>\
        ".format(ticket_id)
    return servicedesk_call(endpoint, call, settings)


def get_task_ticket(ticket_id):
    """Get incident details."""
    endpoint = "TaskTicket.TaskTicketHttpSoap11Endpoint/"
    call = "getTaskTicket"
    settings = "<wrap:ticketIdentifier>{0}</wrap:ticketIdentifier>\
        ".format(ticket_id)
    return servicedesk_call(endpoint, call, settings)


def get_service_request(ticket_id):
    """Get incident details."""
    endpoint = "ServiceRequest.ServiceRequestHttpSoap11Endpoint/"
    call = "getServiceRequest"
    settings = "<wrap:ticketIdentifier>{0}</wrap:ticketIdentifier>\
    ".format(ticket_id)
    return servicedesk_call(endpoint, call, settings)


def list_service_requests(search):
    """List Service Requests."""
    endpoint = "ServiceRequest.ServiceRequestHttpSoap11Endpoint/"
    call = "listServiceRequests"
    settings = "<wrap:searchText>{0}</wrap:searchText>".format(search)
    return servicedesk_call(endpoint, call, settings)


def list_task_tickets(search):
    """List Service Requests."""
    endpoint = "TaskTicket.TaskTicketHttpSoap11Endpoint/"
    call = "listTaskTickets"
    settings = "<wrap:searchText>{0}</wrap:searchText>".format(search)
    return servicedesk_call(endpoint, call, settings)


def list_related_configuration_items(ticket_id):
    """Get incident details."""
    endpoint = "Ticket.TicketHttpSoap11Endpoint/"
    call = "listRelatedConfigurationItems"
    settings = "<wrap:ticketIdentifier>{0}</wrap:ticketIdentifier>\
    ".format(ticket_id)
    return servicedesk_call(endpoint, call, settings)


def return_dictionary_from_response(content):
    """Take API response and parse.  Return JSON as python dictionary."""
    # Pull back everything inbetween responseText tags
    r = re.compile(
        '<ax\d\d\d:responseText>(?P<ResponseText>.+)</ax\d\d\d:responseText>',
        re.DOTALL
    )
    json_data = re.findall(r, content.replace(r"\n", ""))[0]
    return json.loads(json_data)


def get_task_ticket_info(ticket_id):
    """Query for task ticket, and return only fields needed."""
    content = get_task_ticket(ticket_id)
    task_ticket = return_dictionary_from_response(content)
    return task_ticket[0]


def get_config_items_associated_with_ticket(ticket):
    """Get a list of config items from a ticket."""
    ticket_id = ticket["id"]
    content = list_related_configuration_items(ticket_id)
    server_dict = return_dictionary_from_response(content)
    servers = list()

    if len(server_dict) == 0:
        # Task did not have CIs.  Check parent ticket
        parent_id = ticket["parent ticket number"]
        content = list_related_configuration_items(parent_id)
        # print content
        server_dict = return_dictionary_from_response(content)
        # print server_dict

    # Create list of servers assocaited with ticket
    for server in server_dict:
        servers.append(server["Name"])

    return servers


def get_tickets_from_disk():
    """Pull cached ticket information from disk."""
    tickets = dict()
    try:
        with open(ENCODED_FILE, 'rb') as handle_read:
            tickets = pickle.load(handle_read)
        status = True
    except:
        status = False

    return status, tickets


def cache_tickets_to_disk(tickets):
    """Write current list of tickets to disk."""
    with open(ENCODED_FILE, 'wb') as handle_write:
        pickle.dump(tickets, handle_write, protocol=pickle.HIGHEST_PROTOCOL)


def cache_new_ticket_info(t):
    """Set a new ticket in the dictionary."""
    new_ticket = dict()
    ticket_id = t["Case#"]
    psd = "Planned Start Date"
    ped = "Planned End Date"
    md = "Modified Date"
    ptn = "parent ticket number"
    # Build ticket
    new_ticket[ticket_id] = dict()
    new_ticket[ticket_id]["id"] = ticket_id
    new_ticket[ticket_id][md] = t[md]
    # Update the ticket data
    try:
        ticket_info = get_task_ticket_info(ticket_id)
        new_ticket[ticket_id][psd] = ticket_info[psd]
        new_ticket[ticket_id][ped] = ticket_info[ped]
        new_ticket[ticket_id][ptn] = ticket_info[ptn]
        """
        try:
            dt = parser.parse(ticket_info[psd])
            today = datetime.today()
            # if (dt.date() == today.date()):
                # print ticket_id + " goes today."
        except:
            print "No planned start time: " + ticket_id
        """
    except:
        print "Failed to connect to get_task_ticket endpoint."
        # Set modified date to Error so it'll update next run
        new_ticket[ticket_id][md] = "Error"

    return new_ticket


def get_current_task_tickets():
    """Return current list of tickets, cached and new coalesced."""
    content = list_task_tickets(GROUP)
    filtered_tickets = return_dictionary_from_response(content)
    md = "Modified Date"

    ds, tickets = get_tickets_from_disk()
    if not ds:
        # Could not read file off disk.  Query for all current info
        tickets = dict()
        c = 0
        for t in filtered_tickets:
            if (t["Assigned Group"] == GROUP) and (t["Status"] == "Queued"):
                # Build the new ticket and assign it to dictionary
                tickets.update(cache_new_ticket_info(t))
                c += 1
    else:
        # Information was received off disk.  Only update modified tickets
        for t in filtered_tickets:
            if (t["Assigned Group"] == GROUP) and (t["Status"] == "Queued"):
                # If ticket is new
                if (t["Case#"] not in tickets):
                    # Build the new ticket and assign it to dictionary
                    tickets.update(cache_new_ticket_info(t))
                else:
                    # If cached/new modified dates don't match; pull in info
                    if (t[md] != tickets[t["Case#"]][md]):
                        tickets.update(cache_new_ticket_info(t))
                        print "Updated ticket with new info: " + t["Case#"]

    return tickets


def convert_datetime_to_epoch(dt):
    """Convert datetime format to epoch."""
    import time
    return time.mktime(dt.timetuple())


def schedule_maintenance_mode(ticket, server_list):
    """
    Schedule maintenance mode in CA UIM.

    Status: Development
    """
    try:
        start_time = ticket["Planned Start Date"]
        end_time = ticket["Planned End Date"]
        dt_start = parser.parse(start_time)
        dt_end = parser.parse(end_time)
        start_time_epoch = convert_datetime_to_epoch(dt_start)
        end_time_epoch = convert_datetime_to_epoch(dt_end)
    except:
        print "Problem getting start/end times.  Inform ticket creator."
        return 1
    for server in server_list:
        current_time = str(datetime.now())
        print current_time + " server=" + server + ", start_time=" \
            + start_time + ", end_time=" + end_time + ", start_time_epoch=" \
            + str(start_time_epoch) + ", end_time_epoch=" + str(end_time_epoch)
    return 0


def refresh_cache(tickets=dict()):
    """Refresh ticket cache."""
    if (len(tickets) == 0):
        tickets = get_current_task_tickets()
    cache_tickets_to_disk(tickets)


def get_ticket_information(ticket_id):
    """Return information on a specific ticket."""
    tickets = get_current_task_tickets()
    refresh_cache(tickets)
    return tickets[ticket_id]


def test():
    """Run test cases."""
    status = {
        0: "Success",
        1: "Failure"
    }
    ticket = "500-326101"
    t = get_ticket_information(ticket)
    s = get_config_items_associated_with_ticket(t)
    return_code = schedule_maintenance_mode(t, s)
    return status[return_code]

print "Test was a " + str(test())
