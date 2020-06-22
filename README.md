# WheelWay

This repo has two interconnected components:

- a webapp to give walking directions in Brighton, Massachusetts which takes into account the condition and slope of sidewalks. You can see the app at [wheel-way.herokuapp.com]. The basic path-finding is quite good, but **I cannot recommend that you use the app as a sole source of information**.
- A pipeline which takes as input a shapefile of streets and returns a shapefile of possible sidewalks and crosswalks. Each segment has an estimated angle, which is computed by interpolating user-provided GIS data.

The pipeline requires some configuration, and one of my priorities is making this as easy as possible.

## The app

The (app)[wheel-way.herokuapp.com] gives walking directions which account for the condition and slope of sidewalks. Contrast this to Google Maps walking directions, which often do not account for crossing the street.  The slope estimation comes from an interpolation of US Geological Survey data. The condition of the sidewalks has been assessed using a computer vision model from the good people at (Project Sidewalk)[https://github.com/ProjectSidewalk/sidewalk-cv-assets19]. The app finds routes using (Dijkstra's algorithm)[https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm] with different cost functions.

Here's what happens when you enter two addresses and a method:

1. The library (geocoder)[https://geocoder.readthedocs.io/] finds the nearest points on the sidewalks to the entered addresses. (To be more precise, the sidewalks are broken into roughly 2 meter segments, and geocoder finds the closest endpoint of one of those segments.)  Each point has a unique numerical id.
2. The app queries a SQL database (stored with AWS) to find the shortest route. This database has a row for each segment of the sidewalk. A PostGIS extension called (pgrouting)[https://github.com/pgRouting/pgrouting] runs Dijkstra's algorithm to find the shortest path between the points.
3. The query returns a list of sidewalk segments which make up the route. This includes the segements' angles, whether they are part of a crosswalk, and whether they may be obstructed. This tells the app where to draw the lines and what color they should be.
4. The lines are drawn on top of a map via (dash-leaflet)[ https://dash-leaflet.herokuapp.com/].

Some details on route-finding methods:
- **Shortest route:** (Dijkstra's algorithm)[https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm]
- **Minimize slope**: the algorithm initially only looks at a map of edges which angles below two degrees, then four degrees, and so on. If the algorithm is able to find a route, it returns that route. Otherwise, it loosens the angle restriction and tries again.  
- **Balance slope and length:** Dijkstra's algorithm with a custom length function. The "length" of each segment is its actual length times a penalty for its angle. This penalty is quadratic: a sidewalk at six degrees is four times as bad as a sidewalk at three degrees. The slider controls a parameter `alpha` which adjusts the toughness of the penalty. In an equation: `custom_length = length * (1 + alpha * angle)^2`.  

### Why not a linear penalty?

I initially had a penalty which was linear in `angle`, but I found that the slider barely changed the route! Why?  Here's one explanation, but if you're into this kind of thing you should think about it first!

If angles are small, then `sin(x)` is approximately `x` (if `x` is measured in radians). This is the "(small angle approximation)[https://en.wikipedia.org/wiki/Small-angle_approximation]" for sine. It's a pretty good approximation: for angles up to 45 degrees, the error is at most about 10%.  So `length * (1 + alpha * angle)` is very close to `length * (1 + alpha * sin(angle))`, which equals `length + alpha * length * sin(angle)`.  Now if you draw a little picture of this segment and the angle `alpha`, you can see that `length * sin(angle)` is change in elevation along this segment.  In other words, `length + alpha*length*sin(angle)` is approximately `length + alpha * change_in_elevation`.

If you add up `length + alpha * change_in_elevation` along a path, you get `total_length + alpha*net_change_in_elevation`. The net change in elevation is just about the beginning and endpoints of the path, not the path itself! So a linear penalty just makes all paths longer by (approximately) the same factor.  (You could use the absolute value of the angle instead, but the results don't change much.)

## The pipeline

More to come!

