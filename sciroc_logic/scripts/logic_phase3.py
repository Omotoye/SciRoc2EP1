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
                "at_counter",
                "at_current_serving_table",
            ],
            output_keys=["current_poi", "task"],
            input_keys=["task"],
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
        if userdata.task == "report order":
            # result = self.call_nav_service(self.counter)
            result = True
            if result:
                userdata.current_poi = self.counter
                return "at_counter"
        if userdata.task == "deliver order":
            table_req = GetTableObjectRequest()
            table_req.table_state = "current serving"
            # table = get_table_by_state(table_req)
            # result = self.call_nav_service(table.table_id)
            result = True
            if result:
                userdata.current_poi = "table1"
                userdata.task = "announce order arrival"
                return "at_current_serving_table"


###+++++++++++++++++++ HUMAN ROBOT INTERACTION (HRI) +++++++++++++++++++++###


class HRI(smach.State):
    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=[
                "order_reported",
                "missing_reported",
                "wrong_reported",
                "object_taken",
                "order_delivered",
                "wrong_and_missing_order_reported",
            ],
            output_keys=["task"],
            input_keys=[
                "task",
                "missing_drinks",
                "wrong_drinks",
            ],
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

        if userdata.task == "report order":
            hri_goal.mode = 0  # Announce Text
            # hri_goal.text = self.get_announce_text()
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                userdata.task = "check object"
                return "order_reported"

        elif userdata.task == "report missing":
            hri_goal.mode = 0  # Announce Text
            # hri_goal.text = self.get_announce_text()
            # hri_goal.missing_drinks.extend(userdata.missing_drinks)
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                userdata.task = "check object"
                return "missing_reported"

        elif userdata.task == "report wrong":
            hri_goal.mode = 0  # Announce Text
            # hri_goal.text = self.get_announce_text()
            # # hri_goal.wrong_drinks.extend(userdata.wrong_drinks)
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                userdata.task = "check object"
                return "wrong_reported"

        elif userdata.task == "report wrong and missing":
            hri_goal.mode = 0  # Announce Text
            # hri_goal.text = self.get_announce_text()
            # # hri_goal.wrong_drinks.extend(userdata.wrong_drinks)
            # # hri_goal.missing_drinks.extend(userdata.missing_drinks)
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                userdata.task = "check object"
                return "wrong_and_missing_order_reported"

        elif userdata.task == "take item":
            hri_goal.mode = 3  # Take Item
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                userdata.task = "deliver order"
                return "object_taken"
        elif userdata.task == "announce order arrival":
            hri_goal.mode = 4  # Drop Item
            # result = self.call_hri_action(hri_goal)
            result = True
            if result:
                return "order_delivered"


###+++++++++++++++++++ OBJECT DETECTION  +++++++++++++++++++++###


class ObjectDetection(smach.State):
    def __init__(self):
        # from here we define the possible outcomes of the state.
        smach.State.__init__(
            self,
            outcomes=[
                "correct_order",
                "wrong_order",
                "missing_order",
                "wrong_and_missing_order",
            ],
            output_keys=["task", "wrong_drinks", "missing_drinks"],
            input_keys=["task"],
        )

    def call_object_detect(self, goal_req):
        # Creates the SimpleActionClient, passing the type of the action
        # client = actionlib.SimpleActionClient("object_detect", ObjectPerceptionAction)

        # Waits until the action server has started up and started
        # listening for goals.
        # client.wait_for_server()

        # Sends the goal to the action server.
        # client.send_goal(goal_req)

        # Waits for the server to finish performing the action.
        # client.wait_for_result()

        # return the result of executing the action
        # return client.get_result()
        result = ObjDetInterfaceResult()
        result.n_found_tags = 2
        result.found_tags = ["bottle", "fanta"]
        result.match = False
        return result

    def check_wrong_drinks(self, expected_tags, found_tags):
        wrong_drinks = []
        for drink in found_tags:
            if drink not in expected_tags:
                wrong_drinks.append(drink)
        return wrong_drinks

    def check_missing_drinks(self, expected_tags, found_tags):
        missing_drinks = []
        for drink in expected_tags:
            if drink not in found_tags:
                missing_drinks.append(drink)
        return missing_drinks

    def execute(self, userdata):
        object_detect_goal = ObjDetInterfaceGoal()

        if userdata.task == "check object":
            table_req = GetTableObjectRequest()
            table_req.table_state = "current serving"
            # table = get_table_by_state(table_req)
            object_detect_goal.mode = 2  # Comparison
            # object_detect_goal.expected_tags = table.required_drinks
            # result = self.call_object_detect(object_detect_goal)
            result = True
            if result:
                userdata.task = "take item"
                return "correct_order"
            elif result == False:
                missing_drinks = ["", ""]
                wrong_drinks = []
                # missing_drinks = self.check_missing_drinks(
                #     expected_tags=table.required_drinks,
                #     found_tags=result.found_tags,
                # )
                # wrong_drinks = self.check_wrong_drinks(
                #     expected_tags=table.required_drinks,
                #     found_tags=result.found_tags,
                # )
                if len(missing_drinks) > 0:
                    userdata.task = "report missing"
                    userdata.missing_drinks = missing_drinks
                    return "missing_order"
                elif len(wrong_drinks) > 0:
                    userdata.task = "report wrong"
                    userdata.wrong_drinks = wrong_drinks
                    return "wrong_order"
                elif len(wrong_drinks) > 0 and len(missing_drinks) > 0:
                    userdata.task = "report wrong and missing"
                    userdata.missing_drinks = missing_drinks
                    userdata.wrong_drinks = wrong_drinks
                    return "wrong_and_missing_order"


###+++++++++++++++++++ POINT OF INTEREST STATE (POI STATE) +++++++++++++++++++++###


class POI_State(smach.State):
    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=["updated"],
            input_keys=["current_poi"],
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
        update_state_request.table_id = userdata.current_poi
        update_state_request.updated_states = [
            "need serving",
            "already served",
            "current serving",
        ]
        update_state_request.need_serving = False
        update_state_request.already_served = True
        update_state_request.current_serving = False
        # result = self.call_poi_state_service(
        #     update_state_request=update_state_request
        # )
        result = True
        if result:
            return "updated"


if __name__ == "__main__":
    rospy.init_node("sciroc_state_machine")

    Phase3 = smach.StateMachine(outcomes=["phase3_finished"])
    Phase3.userdata.task = "report order"

    # Open the container
    with Phase3:
        smach.StateMachine.add(
            "NAVIGATE",
            Navigate(),
            transitions={
                "at_counter": "HRI(Speak)",
                "at_current_serving_table": "HRI(Speak)",
            },
            remapping={"task": "task"},
        )

        smach.StateMachine.add(
            "HRI(Speak)",
            HRI(),
            transitions={
                "order_reported": "CHECK_OBJECT",
                "missing_reported": "CHECK_OBJECT",
                "wrong_reported": "CHECK_OBJECT",
                "wrong_and_missing_order_reported": "CHECK_OBJECT",
                "object_taken": "NAVIGATE",
                "order_delivered": "UPDATE_POI_STATE",
            },
            remapping={
                "task": "task",
                "missing_drinks": "missing_drinks",
                "wrong_drinks": "wrong_drinks",
            },
        )

        smach.StateMachine.add(
            "CHECK_OBJECT",
            ObjectDetection(),
            transitions={
                "correct_order": "HRI(Speak)",
                "wrong_order": "HRI(Speak)",
                "missing_order": "HRI(Speak)",
                "wrong_and_missing_order": "HRI(Speak)",
            },
            remapping={"task": "task"},
        )

        smach.StateMachine.add(
            "UPDATE_POI_STATE",
            POI_State(),
            transitions={"updated": "phase3_finished"},
            remapping={"current_poi": "current_poi"},
        )

    # Create and start the introspection server
    sis = smach_ros.IntrospectionServer(
        "server_name", Phase3, "SciRoc2EP1 Logic State Machine"
    )
    sis.start()

    # Execute SMACH plan
    outcome = Phase3.execute()

    # Wait for ctrl-c to stop the application
    rospy.spin()
    sis.stop()
