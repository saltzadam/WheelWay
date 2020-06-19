# WheelWay

This repo has two interconnected components:

-- a webapp to give walking directions in Brighton, Massachusetts which take into account the condition and slope of sidewalks. You can see the app at [wheel-way.herokuapp.com]. The basic path-finding is quite good, but **I cannot recommend that you use the app as a sole source of information**.
-- A pipeline which takes as input a shapefile of streets and returns a shapefile of possible sidewalks and crosswalks. Each segment has an estimated angle, which is computed by interpolating user-provided GIS data.

The pipeline requires some configuration, and one of my priorities is making this as easy as possible.


