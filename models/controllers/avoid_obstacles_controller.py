#!/usr/bin/python
# -*- Encoding: utf-8 -*

from math import *

from utils import linalg2_util as linalg
from utils import math_util

class AvoidObstaclesController:

  def __init__( self, supervisor ):
    # bind the supervisor
    self.supervisor = supervisor

    # sensor placements
    self.proximity_sensor_placements = supervisor.proximity_sensor_placements()

    # sensor gains (weights)
    self.sensor_gains = [   1.0-( (0.9*abs(p.theta)) / pi )   for p in supervisor.proximity_sensor_placements() ]

    # control gains
    self.kP = 10.0
    self.kI = 0.5
    self.kD = 0.1
    
    # stored values - for computing next results
    self.prev_time = 0.0
    self.prev_eP = 0.0
    self.prev_eI = 0.0

    # additional calculated values 
    self.obstacle_vectors_rel = [ [ 0.0, 0.0 ] ] * len( self.proximity_sensor_placements )
    self.obstacle_vectors_abs = [ [ 0.0, 0.0 ] ] * len( self.proximity_sensor_placements )
    self.heading_vector = [ 0.0, 0.0 ]

  def execute( self ):
    # get the distances indicated by the robot's sensor readings
    sensor_distances = self.supervisor.proximity_sensor_real_distances()

    # calculate the position of detected obstacles and find an avoidance vector
    heading_vector = [ 0.0, 0.0 ]        # initialize the heading vector
    robot_pos, robot_theta = self.supervisor.estimated_pose().vunpack()
    for i in range( len( sensor_distances ) ):
      # calculate the position of the obstacle
      sensor_pos, sensor_theta = self.proximity_sensor_placements[i].vunpack()
      vector = [ sensor_distances[i], 0.0 ]
      vector = linalg.rotate_and_translate_vector( vector, sensor_theta, sensor_pos )
      self.obstacle_vectors_rel[i] = vector   # store the obstacle vectors in the robot's reference frame
      vector = linalg.rotate_and_translate_vector( vector, robot_theta, robot_pos )
      self.obstacle_vectors_abs[i] = vector   # store the obstacle vectors in the estimated world reference frame
       
      # accumluate the heading vector within the robot's reference frame
      heading_vector = linalg.sub(  heading_vector,
                                    linalg.scale( self.obstacle_vectors_rel[i], self.sensor_gains[i] ) )

    # convert the final heading vector to the estimated world reference frame
    heading_vector = linalg.rotate_and_translate_vector( heading_vector, robot_theta, robot_pos )
    self.heading_vector = heading_vector
    
    # calculate the desired heading
    theta_d = atan2( heading_vector[1], heading_vector[0] )

    # calculate the time that has passed since the last control iteration
    current_time = self.supervisor.time()
    dt = current_time - self.prev_time

    # calculate the error terms
    eP = math_util.normalize_angle( theta_d - robot_theta )
    eI = self.prev_eI + eP*dt
    eD = ( eP - self.prev_eP ) / dt

    # calculate angular velocity
    omega = self.kP * eP + self.kI * eI + self.kD * eD
    
    # calculate translational velocity
    # velocity is v_max when omega is 0,
    # drops rapidly to zero as |omega| rises
    v_max = 2.0 # TODO: move this
    v = v_max / ( abs( omega ) + 1 )**2

    # store values for next control iteration
    self.prev_time = current_time
    self.prev_eP = eP
    self.prev_eI = eI

    self.supervisor.set_outputs( v, omega )