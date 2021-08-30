#!/usr/bin/env python

import rospy

# importing the labrary for the creation of the state machine
import smach
import smach_ros


# Brings in the SimpleActionClient
import actionlib
from actionlib_msgs.msg._GoalStatus import GoalStatus

# navigation service message
from sciroc_navigation.srv import GoToPOI

# message for updating and the getting the state of the POI (Point of Interest)
from sciroc_poi_state.srv import UpdatePOIState, GetTableObject
from sciroc_poi_state.srv import UpdatePOIStateRequest, GetTableObjectRequest

# people perception package
# from people_perception.msg import (
#     PeopleCounterAction,
#     PeopleCounterGoal,
#     PeopleCounterResult,
# )

# human robot interaction package
from sciroc_hri.msg import HRIAction, HRIGoal, HRIResult

from sciroc_objdet.msg import (
    ObjDetInterfaceAction,
    ObjDetInterfaceGoal,
    ObjDetInterfaceResult,
)

require_table = ["table1", "table3"]

poi = ["counter", "t1", "t2", "t3", "t4", "t5", "t6"]


def get_table_by_state(req):
    rospy.wait_for_service("get_table_object")
    try:
        poi_state = rospy.ServiceProxy("get_table_object", GetTableObject)
        req.mode = 0
        table = poi_state(req)
        return table
    except rospy.ServiceException as e:
        print("Service call failed: {e}".format(e=e))


def get_table_by_id(req):
    rospy.wait_for_service("get_table_object")
    try:
        poi_state = rospy.ServiceProxy("get_table_object", GetTableObject)
        req.mode = 1
        table = poi_state(req)
        return table
    except rospy.ServiceException as e:
        print("Service call failed: {e}".format(e=e))


###+++++++++++++++++++ NAVIGATION +++++++++++++++++++++###


class Navigate(smach.State):
    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=[
                "at_require_order_table",
            ],
            output_keys=["current_poi"],
        )
        # This would be changed later, only here for testing reasons
        self.poi = poi[1:]
        self.counter = poi[0]

    def call_nav_service(self, next_poi):
        rospy.wait_for_service("go_to_poi_service")
        try:
            go_to_poi = rospy.ServiceProxy("go_to_poi_service", GoToPOI)
            result = go_to_poi(next_poi)

            if result.result == "goal reached":
                return True
            else:
                print("Point of interest [{poi}] does not exist".format(poi=poi))
                return False
        except rospy.ServiceException as e:
            print("Service call failed: {e}".format(e=e))

    def execute(self, userdata):

        table_req = GetTableObjectRequest()
        table_req.table_state = "require order"
        # table = get_table_by_state(table_req)
        # if len(table.require_order_list) > 0:

        # result = self.call_nav_service(table.table_id)
        result = True
        if result:
            # userdata.current_poi = table.table_id
            userdata.current_poi = require_table.pop()
            return "at_require_order_table"


###+++++++++++++++++++ HUMAN ROBOT INTERACTION (HRI) +++++++++++++++++++++###


class HRI(smach.State):
    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=[
                "order_taken",
            ],
            output_keys=["order_list"],
        )

    def get_announce_text(self):
        pass

    def call_hri_action(self, goal_req):
        # Creates the SimpleActionClient, passing the type of the action
        # client = actionlib.SimpleActionClient("hri", HRIAction)

        # Waits until the action server has started up and started
        # listening for goals.
        # client.wait_for_server()

        # Sends the goal to the action server.
        # client.send_goal(goal_req)

        # Waits for the server to finish performing the action.
        # client.wait_for_result()

        # return the result of executing the action
        # return client.get_result()
        result = HRIResult()
        result.result = True
        result.order_list = ["", "", ""]

    def execute(self, userdata):

        hri_goal = HRIGoal()

        hri_goal.mode = 1  # Take Order
        # result = self.call_hri_action(hri_goal)
        result = True
        if result:
            # userdata.order_list = result.required_drinks
            userdata.order_list = ["fanta", "malt", "cocacola"]
            return "order_taken"


###+++++++++++++++++++ POINT OF INTEREST STATE (POI STATE) +++++++++++++++++++++###


class POI_State(smach.State):
    def __init__(self):
        smach.State.__init__(
            self, outcomes=["updated"], input_keys=["current_poi", "order_list"]
        )

    def call_poi_state_service(self, update_state_request=UpdatePOIStateRequest()):

        rospy.wait_for_service("update_poi_state")
        try:
            update_state = rospy.ServiceProxy("update_poi_state", UpdatePOIState)
            result = update_state(update_state_request)

            if result.result == "updated" or result.result == "saved":
                return True
        except rospy.ServiceException as e:
            print("Service call failed: {e}".format(e=e))

    def execute(self, userdata):

        update_state_request = UpdatePOIStateRequest()
        update_state_request.task = "update"
        update_state_request.table_id = userdata.current_poi
        update_state_request.updated_states = [
            "require order",
            "required drinks",
            "current serving",
        ]
        update_state_request.require_order = False
        update_state_request.current_serving = True
        update_state_request.required_drinks = userdata.order_list

        # result = self.call_poi_state_service(
        #     update_state_request=update_state_request
        # )
        result = True
        if result:
            return "updated"


if __name__ == "__main__":
    rospy.init_node("sciroc_state_machine")

    Phase2 = smach.StateMachine(outcomes=["phase2_finished"])

    # Open the container
    with Phase2:
        smach.StateMachine.add(
            "NAVIGATE",
            Navigate(),
            transitions={
                "at_require_order_table": "HRI(TakeOrder)",
            },
        )

        smach.StateMachine.add(
            "HRI(TakeOrder)",
            HRI(),
            transitions={"order_taken": "UPDATE_POI_STATE"},
        )

        smach.StateMachine.add(
            "UPDATE_POI_STATE",
            POI_State(),
            transitions={"updated": "phase2_finished"},
            remapping={
                "current_poi": "current_poi",
                "order_list": "order_list",
            },
        )

    # Create and start the introspection server
    sis = smach_ros.IntrospectionServer(
        "server_name", Phase2, "SciRoc2EP1 Logic State Machine"
    )
    sis.start()

    # Execute SMACH plan
    outcome = Phase2.execute()

    # Wait for ctrl-c to stop the application
    rospy.spin()
    sis.stop()