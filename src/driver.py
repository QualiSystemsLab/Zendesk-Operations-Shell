from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext
#from data_model import *  # run 'shellfoundry generate' to generate data model classes
import json
import requests
import cloudshell.api.cloudshell_api as csapi
import time
import datetime

class ZendeskOperationsShellDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        # See below some example code demonstrating how to return the resource structure and attributes
        # In real life, this code will be preceded by SNMP/other calls to the resource details and will not be static
        # run 'shellfoundry generate' in order to create classes that represent your data model

        '''
        resource = ZendeskOperationsShell.create_from_context(context)
        resource.vendor = 'specify the shell vendor'
        resource.model = 'specify the shell model'

        port1 = ResourcePort('Port 1')
        port1.ipv4_address = '192.168.10.7'
        resource.add_sub_resource('1', port1)

        return resource.create_autoload_details()
        '''
        return AutoLoadDetails([], [])

    # </editor-fold>

    # <editor-fold desc="Help Functions">

    def create_a_session(self, host, domain, token):
        cs_session = csapi.CloudShellAPISession(host=host, domain=domain, token_id=token)
        return cs_session

    def get_global_inputs(self, reservationId, cs_session):
        global_inputs = cs_session.GetReservationInputs(reservationId).GlobalInputs
        for tempVar in global_inputs:
            if tempVar.ParamName == 'user':
                user = tempVar.Value
            if tempVar.ParamName == 'pwd':
                pwd = tempVar.Value
        return user, pwd

    def get_tickets_vector(self, reservationId, headers, cs_session, user, pwd, switchVariable, url):
        Tickets_Vector = []
        while switchVariable == 1:

            getting_all_the_tickets = requests.get(url, auth=(user, pwd), headers=headers)

            if getting_all_the_tickets.status_code != 200:
                cs_session.WriteMessageToReservationOutput(reservationId=reservationId,
                                                           message='Status: {0} Problem With Authentication.'.format(
                                                               getting_all_the_tickets.status_code))
                exit()

            Decoded_Json_For_Tickets = getting_all_the_tickets.json()
            Number_Of_Tickets = len(Decoded_Json_For_Tickets['tickets'])

            for i in range(0, Number_Of_Tickets):
                ticket_id = Decoded_Json_For_Tickets['tickets'][i]['id']
                ticket_id = str(ticket_id)
                Tickets_Vector.append(ticket_id)

            nextPage = Decoded_Json_For_Tickets['next_page']

            if nextPage != None:
                url = nextPage
            else:
                switchVariable = 0
        return Tickets_Vector

    def get_users_vector(self, reservationId, headers, cs_session, user, pwd, switchVariable, url):
        Users_ID_Vector = []
        while switchVariable == 1:

            getting_all_the_users = requests.get(url, auth=(user, pwd), headers=headers)

            if getting_all_the_users.status_code != 200:
                cs_session.WriteMessageToReservationOutput(reservationId=reservationId,
                                                           message='Status: {0} Problem With Authentication.'.format(
                                                               getting_all_the_users.status_code))
                exit()

            Decoded_Json_For_Users = getting_all_the_users.json()
            Number_Of_Users = len(Decoded_Json_For_Users['users'])

            for i in range(0, Number_Of_Users):
                user_id = Decoded_Json_For_Users['users'][i]['id']
                user_id = str(user_id)
                Users_ID_Vector.append(user_id)

            nextPage = Decoded_Json_For_Users['next_page']

            if nextPage != None:
                url = nextPage
            else:
                switchVariable = 0
        return Users_ID_Vector

    def suspend_function(self, user_id, user, pwd, headers):
        url_for_user_details = 'https://qualisystemscom.zendesk.com/api/v2/users/' + user_id + '.json'
        data = {'user': {'suspended': 'true'}}
        payload = json.dumps(data)
        requests.put(url_for_user_details, data=payload, auth=(user, pwd), headers=headers)

    def unsuspend_function(self, user_id, user, pwd, headers):
        url_for_user_details = 'https://qualisystemscom.zendesk.com/api/v2/users/' + user_id + '.json'
        data = {'user': {'suspended': 'false'}}
        payload = json.dumps(data)
        unsuspend_the_user = requests.put(url_for_user_details, data=payload, auth=(user, pwd), headers=headers)

        if unsuspend_the_user.status_code != 200:
            cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                       message='Status: {0} Problem With Authentication.'.format(
                                                           unsuspend_the_user.status_code))
            exit()

    def add_comment_and_close_the_tickets(self, cs_session, input_key, Tickets_Vector,  user, pwd, headers_get, headers_put, resid):

        for i in range(0, len(Tickets_Vector)):
            url_for_user_id='https://qualisystemscom.zendesk.com/api/v2/tickets/' + Tickets_Vector[i] + '.json'
            getting_user_id = requests.get(url_for_user_id, auth=(user, pwd), headers=headers_get)
            Decoded_Json_For_User_ID = getting_user_id.json()
            user_id = Decoded_Json_For_User_ID['ticket']['requester_id']

            url_for_user_name ='https://qualisystemscom.zendesk.com/api/v2/users/'+str(user_id)+'.json'
            getting_user_name = requests.get(url_for_user_name, auth=(user, pwd), headers=headers_get)
            Decoded_Json_For_User_Name = getting_user_name.json()
            name = Decoded_Json_For_User_Name['user']['name']
            name=str(name)
            name=name.partition(' ')[0]

            body = """Hi """+name+""",
We're sorry to hear that you are no longer under a support agreement with Quali.
We will go ahead and close this ticket however if you ever require our services in the future we will be happy to continue working with you.

Best wishes,

Quali Support."""
            data = {"ticket": {"comment": {"body": body}, "status": "closed"}}
            payload = json.dumps(data)

            if input_key == '1234321':
                    url_for_one_ticket = 'https://qualisystemscom.zendesk.com/api/v2/tickets/' + Tickets_Vector[i] + '.json'
                    requests.put(url_for_one_ticket, data=payload, auth=(user, pwd),
                                                                    headers=headers_put)
        if input_key == '1234321':
            cs_session.WriteMessageToReservationOutput(resid, 'All Tickets Were Closed Successfully')

    def get_users_vectors(self, reservationId, headers, cs_session, user, pwd, switchVariable, userDateInTimeStamp):
        Users_ID_Vector = []
        Active_Users_ID_Vector = []
        UnActive_Users_ID_Vector = []
        Users_With_No_Last_Login_Info_ID_Vector = []
        url_for_all_users = 'https://qualisystemscom.zendesk.com/api/v2/users.json'

        while switchVariable == 1:

            getting_all_the_users = requests.get(url_for_all_users, auth=(user, pwd), headers=headers)

            if getting_all_the_users.status_code != 200:
                cs_session.WriteMessageToReservationOutput(reservationId=reservationId,
                                                           message='Status: {0} Problem With Authentication.'.format(
                                                               getting_all_the_users.status_code))
                exit()

            Decoded_Json_For_Users = getting_all_the_users.json()
            Number_Of_Users = len(Decoded_Json_For_Users['users'])

            for i in range(0, Number_Of_Users):

                user_id = Decoded_Json_For_Users['users'][i]['id']
                user_id = str(user_id)
                Users_ID_Vector.append(user_id)
                last_login_at = (Decoded_Json_For_Users['users'][i]['last_login_at'])
                if last_login_at == None:
                    Users_With_No_Last_Login_Info_ID_Vector.append(user_id)
                else:
                    timeStampInSec = time.mktime(
                        datetime.datetime.strptime(last_login_at, "%Y-%m-%dT%H:%M:%SZ").timetuple())
                    if timeStampInSec > userDateInTimeStamp:
                        Active_Users_ID_Vector.append(user_id)
                    else:
                        UnActive_Users_ID_Vector.append(user_id)

            nextPage = Decoded_Json_For_Users['next_page']

            if nextPage != None:
                url_for_all_users = nextPage
            else:
                switchVariable = 0

        return Users_ID_Vector, Users_With_No_Last_Login_Info_ID_Vector, Active_Users_ID_Vector, UnActive_Users_ID_Vector



    # </editor-fold>

    # <editor-fold desc="Operations">

    def update_global_inputs(self, context, input_user_mail, input_user_pwd):
        resid = context.reservation.reservation_id
        cs_session=self.create_a_session(context.connectivity.server_address, context.reservation.domain, context.connectivity.admin_auth_token)
        cs_session.UpdateReservationGlobalInputs(reservationId=resid,globalInputs=[csapi.UpdateTopologyGlobalInputsRequest('user',input_user_mail),csapi.UpdateTopologyGlobalInputsRequest('pwd',input_user_pwd)])
        user,pwd=self.get_global_inputs(resid,cs_session)
        cs_session.WriteMessageToReservationOutput(reservationId=resid, message='Global Inputs Successfully Updated\nUser Email Entered: {0}\nUser Password Entered: {1}'.format(user, pwd))

    def create_a_new_user(self, context, input_user_name, input_user_email, input_user_role, input_user_org):
        resid = context.reservation.reservation_id
        headers = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url = 'https://qualisystemscom.zendesk.com/api/v2/users.json'
        data = {'user': {'name': input_user_name, 'email': input_user_email, 'role': input_user_role,
                         'organization_id': input_user_org}}
        payload = json.dumps(data)
        create_user = requests.post(url, data=payload, auth=(user, pwd), headers=headers)

        if create_user.status_code != 201:
            cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                       message='Status: {0} Problem With Authentication.'.format(
                                                           create_user.status_code))
            exit()

        cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                   message='User Created successfully\n')

        Decoded_Json_For_User = create_user.json()
        user_id = Decoded_Json_For_User['user']['id']
        name = Decoded_Json_For_User['user']['name']
        email = Decoded_Json_For_User['user']['email']
        role = Decoded_Json_For_User['user']['role']
        organization = Decoded_Json_For_User['user']['organization_id']

        return (
        "User ID : {0}\nUser Name : {1}\nUser Email : {2}\nUser Role : {3}\nUser Organization ID : {4}".format(user_id,
                                                                                                               name,
                                                                                                               email,
                                                                                                               role,
                                                                                                               organization))

    def get_user_id_by_name(self, context, input_user_name):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_user_id = 'https://qualisystemscom.zendesk.com/api/v2/users/search.json?query=' + input_user_name

        getting_user_id = requests.get(url_for_user_id, auth=(user, pwd), headers=headers)

        if getting_user_id.status_code != 200:
            cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                       message='Status: {0} Problem With Authentication.'.format(
                                                           getting_user_id.status_code))
            exit()

        Decoded_Json_For_User_ID = getting_user_id.json()
        user_id = Decoded_Json_For_User_ID['users'][0]['id']
        name = Decoded_Json_For_User_ID['users'][0]['name']
        email = Decoded_Json_For_User_ID['users'][0]['email']

        return ("Input Entered : {3}\nUser Name : {0}\nUser Email : {1}\nUser ID : {2}".format(name, email, user_id,
                                                                                               input_user_name))

    def get_organization_id_by_name(self, context, input_org_name):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_org_id = 'https://qualisystemscom.zendesk.com/api/v2/organizations/autocomplete.json?name=' + input_org_name

        getting_org_id = requests.get(url_for_org_id, auth=(user, pwd), headers=headers)

        if getting_org_id.status_code != 200:
            cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                       message='Status: {0} Problem With Authentication.'.format(
                                                           getting_org_id.status_code))
            exit()

        Decoded_Json_For_Organization_ID = getting_org_id.json()
        org_id = Decoded_Json_For_Organization_ID['organizations'][0]['id']
        name = Decoded_Json_For_Organization_ID['organizations'][0]['name']

        return (
        "Input Entered : {2}\nOrganization Name : {0}\nOrganization ID : {1}".format(name, org_id, input_org_name))

    def get_all_user_tickets(self, context, user_id):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_all_user_tickets = 'https://qualisystemscom.zendesk.com/api/v2/users/' + user_id + '/tickets/requested.json'
        Tickets_Vector=self.get_tickets_vector(resid,headers,cs_session,user,pwd,1,url_for_all_user_tickets)

        return ("User ID : {2}\nNumber Of User Tickets : {0}\nTickets Numbers : {1}".format(len(Tickets_Vector),Tickets_Vector,user_id))

    def get_all_organization_tickets(self, context, org_id):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_all_organization_tickets = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + org_id + '/tickets.json'
        Tickets_Vector = self.get_tickets_vector(resid, headers, cs_session, user, pwd, 1, url_for_all_organization_tickets)

        return (
        "Organization ID : {2}\nNumber Of Organization Tickets : {0}\nTickets Numbers : {1}".format(len(Tickets_Vector),
                                                                                                    Tickets_Vector,
                                                                                                    org_id))

    def get_all_organization_users(self, context, org_id):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_all_organization_users = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + org_id + '/users.json'
        Users_ID_Vector = self.get_users_vector(resid, headers, cs_session, user, pwd, 1, url_for_all_organization_users)

        return (
        "Organization ID : {2}\nNumber Of Organization Users : {0}\nUsers ID Numbers : {1}".format(len(Users_ID_Vector),
                                                                                                   Users_ID_Vector,
                                                                                                   org_id))

    def suspend_a_user_and_close_all_his_tickets(self, context, user_id, input_key):
        resid = context.reservation.reservation_id
        headers_get = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_all_user_tickets = 'https://qualisystemscom.zendesk.com/api/v2/users/' + user_id + '/tickets/requested.json'
        Tickets_Vector = self.get_tickets_vector(resid, headers_get, cs_session, user, pwd, 1, url_for_all_user_tickets)

        headers_put = {'Content-Type': 'application/json'}

        self.add_comment_and_close_the_tickets(cs_session, input_key, Tickets_Vector, user, pwd, headers_get, headers_put, resid)

        self.suspend_function(user_id, user, pwd, headers_put)
        cs_session.WriteMessageToReservationOutput(resid, 'User Suspended Successfully')

    def unsuspend_a_user(self, context, user_id):
        resid = context.reservation.reservation_id
        headers = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        self.unsuspend_function(user_id, user, pwd, headers)
        cs_session.WriteMessageToReservationOutput(resid, 'User UnSuspended Successfully')

    def suspend_all_organization_users_and_close_all_its_tickets(self, context, org_id, input_key):
        resid = context.reservation.reservation_id
        headers_get = {'Accept': 'application/json'}
        headers_put = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)


        url_for_all_organization_tickets = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + org_id + '/tickets.json'
        Tickets_Vector = self.get_tickets_vector(resid, headers_get, cs_session, user, pwd, 1,
                                                 url_for_all_organization_tickets)

        self.add_comment_and_close_the_tickets(cs_session, input_key, Tickets_Vector,  user, pwd, headers_get, headers_put, resid)

        url_for_all_organization_users = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + org_id + '/users.json'
        Users_ID_Vector = self.get_users_vector(resid, headers_get, cs_session, user, pwd, 1,
                                                url_for_all_organization_users)

        for i in range(0, len(Users_ID_Vector)):
            self.suspend_function(Users_ID_Vector[i], user, pwd, headers_put)
        cs_session.WriteMessageToReservationOutput(resid, 'Organization Users Suspended Successfully')

    def unsuspend_all_organization_users(self, context, org_id):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url_for_all_organization_users = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + org_id + '/users.json'
        Users_ID_Vector = self.get_users_vector(resid, headers, cs_session, user, pwd, 1,
                                                url_for_all_organization_users)

        headers = {'Content-Type': 'application/json'}
        for i in range(0, len(Users_ID_Vector)):
            self.unsuspend_function(Users_ID_Vector[i], user, pwd, headers)
        cs_session.WriteMessageToReservationOutput(resid, 'Organization Users UnSuspended Successfully')

    def Get_all_users_who_have_loggedIn_since_entered_date(self, context, user_input_date, user_validation_key):
        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        cs_session.WriteMessageToReservationOutput(reservationId=resid,message='Date Entered : {0}\n'.format(user_input_date))
        userDateInTimeStamp = time.mktime(datetime.datetime.strptime(user_input_date,"%d/%m/%Y" ).timetuple())

        Users_ID_Vector, Users_With_No_Last_Login_Info_ID_Vector, Active_Users_ID_Vector, UnActive_Users_ID_Vector = self.get_users_vectors(
            resid, headers, cs_session, user, pwd, 1, userDateInTimeStamp)

        headers = {'Content-Type': 'application/json'}
        if user_validation_key == '1234321':
            currentDate=time.strftime("%d-%m-%Y")
            file=open('C:\UnActive Users Vector {0}.txt'.format(currentDate),'w')
            file.write('{0}'.format(UnActive_Users_ID_Vector))
            file.close()

            for i in range(0, len(UnActive_Users_ID_Vector)):
                self.suspend_function(UnActive_Users_ID_Vector[i], user, pwd, headers)
            cs_session.WriteMessageToReservationOutput(resid,'All UnActive Users From Entered Date Suspended Successfully\n')

        return (
        "Number Of All Users : {0}\nNumber Of Active Users From Entered Date : {1}\nNumber Of UnActive Users From Entered Date : {2}\nNumber Of Users With No Last Login Info : {3}".format(
            len(Users_ID_Vector), len(Active_Users_ID_Vector), len(UnActive_Users_ID_Vector),
            len(Users_With_No_Last_Login_Info_ID_Vector)))

    def unsuspend_all_users_from_users_id_vector(self, context, users_id_vector):
        resid = context.reservation.reservation_id
        headers = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        Users_ID_Vector = users_id_vector
        Users_ID_Vector = Users_ID_Vector.split("['")[1]
        Users_ID_Vector = Users_ID_Vector.split("']")[0]
        Users_ID_Vector = Users_ID_Vector.split("', '")

        for i in range(0, len(Users_ID_Vector)):
            self.unsuspend_function(Users_ID_Vector[i], user, pwd, headers)
        cs_session.WriteMessageToReservationOutput(resid, 'All Users From The Vector UnSuspended Successfully')

    # </editor-fold>




    # <editor-fold desc="Orchestration Save and Restore Standard">
    def orchestration_save(self, context, cancellation_context, mode, custom_params):
      """
      Saves the Shell state and returns a description of the saved artifacts and information
      This command is intended for API use only by sandbox orchestration scripts to implement
      a save and restore workflow
      :param ResourceCommandContext context: the context object containing resource and reservation info
      :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
      :param str mode: Snapshot save mode, can be one of two values 'shallow' (default) or 'deep'
      :param str custom_params: Set of custom parameters for the save operation
      :return: SavedResults serialized as JSON
      :rtype: OrchestrationSaveResult
      """

      # See below an example implementation, here we use jsonpickle for serialization,
      # to use this sample, you'll need to add jsonpickle to your requirements.txt file
      # The JSON schema is defined at:
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/saved_artifact_info.schema.json
      # You can find more information and examples examples in the spec document at
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/save%20%26%20restore%20standard.md
      '''
            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.

            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.
            identifier = created_date.strftime('%y_%m_%d %H_%M_%S_%f')

            orchestration_saved_artifact = OrchestrationSavedArtifact('REPLACE_WITH_ARTIFACT_TYPE', identifier)

            saved_artifacts_info = OrchestrationSavedArtifactInfo(
                resource_name="some_resource",
                created_date=created_date,
                restore_rules=OrchestrationRestoreRules(requires_same_resource=True),
                saved_artifact=orchestration_saved_artifact)

            return OrchestrationSaveResult(saved_artifacts_info)
      '''
      pass

    def orchestration_restore(self, context, cancellation_context, saved_artifact_info, custom_params):
        """
        Restores a saved artifact previously saved by this Shell driver using the orchestration_save function
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
        :param str saved_artifact_info: A JSON string representing the state to restore including saved artifacts and info
        :param str custom_params: Set of custom parameters for the restore operation
        :return: None
        """
        '''
        # The saved_details JSON will be defined according to the JSON Schema and is the same object returned via the
        # orchestration save function.
        # Example input:
        # {
        #     "saved_artifact": {
        #      "artifact_type": "REPLACE_WITH_ARTIFACT_TYPE",
        #      "identifier": "16_08_09 11_21_35_657000"
        #     },
        #     "resource_name": "some_resource",
        #     "restore_rules": {
        #      "requires_same_resource": true
        #     },
        #     "created_date": "2016-08-09T11:21:35.657000"
        #    }

        # The example code below just parses and prints the saved artifact identifier
        saved_details_object = json.loads(saved_details)
        return saved_details_object[u'saved_artifact'][u'identifier']
        '''
        pass

    # </editor-fold>



