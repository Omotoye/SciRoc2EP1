#!/usr/bin/env python

import rospy
from sciroc_poi_state.srv import SetPOIState, GetPOIState, UpdatePOIState
from sciroc_poi_state.srv import SetPOIStateResponse, GetPOIStateResponse, UpdatePOIStateResponse

# Brings in the messages used by the go_to_poi service

POI = {}  # for storing all the table objects


class Table:
    def __init__(self, table_id, no_of_people, no_of_object):
        self.table_id = table_id
        self.no_of_people = no_of_people
        self.no_of_object = no_of_object
        self.need_serving = False
        self.need_cleaning = False
        self.require_order = False  # the customer needs the robot to take their order
        self.already_served = False
        self.required_drinks = []

        if (no_of_people == 0 and no_of_object == 0):
            self.table_state = 'ready'  # the table is ready to accept new customers

        elif (no_of_people > 0 and no_of_object == 0):
            self.table_state = 'need serving'
            self.need_serving = True
            self.require_order = True

        elif (no_of_people > 0 and no_of_object > 0):
            self.table_state = 'already served'
            self.already_served = True

        elif (no_of_people == 0 and no_of_object > 0):
            self.table_state = 'need cleaning'
            self.need_cleaning = True

    def update_state(self, req):
        for state in req.updated_states:
            if state == 'need serving':
                self.need_serving = req.need_serving
            elif state == 'require order':
                self.require_order = req.require_order
            elif state == 'required drinks':
                self.required_drinks = req.required_drinks
            elif state == 'no of objects':
                self.no_of_object = req.no_of_object
            elif state == 'no of people':
                self.no_of_people = req.no_of_people
            elif state == 'need cleaning':
                self.need_cleaning = req.need_cleaning
            elif state == 'already served':
                self.already_served = req.already_served

        if (self.need_serving == False and self.require_order == False and self.need_cleaning == False and self.already_served == False):
            self.table_state = 'ready'
        if (self.need_serving == True and self.require_order == True and self.need_cleaning == False and self.already_served == False):
            self.table_state = 'need serving'
        if (self.need_serving == False and self.require_order == False and self.need_cleaning == False and self.already_served == True):
            self.table_state = 'already served'
        if (self.need_serving == False and self.require_order == False and self.need_cleaning == True and self.already_served == False):
            self.table_state = 'need cleaning'

        return True


def set_poi_state(req):
    global POI
    table_id = req.table_id
    no_of_people = req.no_of_people
    no_of_object = req.no_of_object

    POI[table_id] = Table(
        table_id=table_id, no_of_people=no_of_people, no_of_object=no_of_object)
    return SetPOIStateResponse('saved')


def get_poi_state(req):
    # Do something
    return GetPOIStateResponse()


def update_poi_state(req):
    global POI
    table_id = req.table_id
    result = POI[table_id].update_state(req)
    if result:
        response = 'updated'
    return UpdatePOIStateResponse(response)


def main():
    rospy.init_node('POI_state')
    s1 = rospy.Service('set_poi_state', SetPOIState, set_poi_state)
    s2 = rospy.Service('get_poi_state', GetPOIState, get_poi_state)
    s3 = rospy.Service('update_poi_state', UpdatePOIState, update_poi_state)
    rospy.spin()


if __name__ == "__main__":
    main()