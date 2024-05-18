"""
Description:    A utility module for working with geometry data
Author:         Amir Khaefi Ashkezari
Date Created:   May 18, 2024 - 23:20:07
"""

import hou


class GeometryData:
    def __init__(self, node) -> None:
        self.node: hou.Node = node
        self.geometry: hou.Geometry = hou.Geometry()

        self.initGeometry()
    # end __init__
        
    def initGeometry(self) -> None:
        geo_ptc_parm: hou.Parm = self.node.parm('geo_ptc')
        geo_ptc: hou.Geometry = geo_ptc_parm.evalAsGeometry()

        if geo_ptc:
            self.geometry.copy(geo_ptc)

        if not self.geometry.points():
            orient_attrib: hou.Attrib = self.geometry.addAttrib(
                hou.attribType.Point, 'orient', [0.0, 0.0, 0.0, 0.0])
            scale_attrib: hou.Attrib = self.geometry.addAttrib(
                hou.attribType.Point, 'scale', [1.0, 1.0, 1.0])
            pscale_attrib: hou.Attrib = self.geometry.addAttrib(
                hou.attribType.Point, 'pscale', 1.0)
            id_attrib: hou.Attrib = self.geometry.addAttrib(
                hou.attribType.Point, 'id', 0)
            orient_attrib.setOption('type', 'quaternion')
            scale_attrib.setOption('type', 'vector')
            pscale_attrib.setOption('type', 'float')
            id_attrib.setOption('type', 'int')
    # end initGeometry
        
    def updateGeometryData(self) -> None:
        """ Replace geometry data parm with geometry property. 
        """
        self.node.parm('geo_ptc').set(self.geometry)
    # end updateGeometryData

    def getLastPoint(self) -> tuple[hou.Point, int]:
        """ Get the last point and it's id from the geometry. 
        """
        if self.geometry and self.geometry.points():
            last_pt: hou.Point = self.geometry.iterPoints()[-1]
            last_id = last_pt.attribValue('id')
            return (last_pt, last_id)

        return (None, 0)
    # end getLastPoint
    
    def genPointcloud(self, position) -> None:
        """ generate a point and assign id. 
        """
        _, last_id = self.getLastPoint()
        pt: hou.Point = self.geometry.createPoint()
        pt.setPosition(position)
        pt.setAttribValue('id', last_id + 1)

        self.updateGeometryData()
    # end genPointcloud

    @staticmethod
    def getPointTransform(point: hou.Point) -> \
        tuple[hou.Vector3, hou.Vector3, hou.Vector3, float]:
        """ Extract Point Transform. 
        """
        position: hou.Vector3 = point.position()
        orient: hou.Quaternion = hou.Quaternion(point.attribValue('orient'))
        rot: hou.Vector3 = orient.extractEulerRotates()
        scale: hou.Vector3 = hou.Vector3(point.attribValue('scale'))
        uniformscale = point.attribValue('pscale')

        return (position, rot, scale, uniformscale)
    # end getPointTransform

    def setPointTransform(self, parms: dict, point: hou.Point) -> None:
        """ Set Point Transform based on handle parms. 
        """
        point.setPosition((parms['tx'], parms['ty'], parms['tz']))
        rot: hou.Vector3 = hou.Vector3((parms['rx'], parms['ry'], parms['rz']))
        orient: hou.Quaternion = hou.Quaternion(hou.hmath.buildRotate(rot))
        point.setAttribValue('orient', orient)
        scale: hou.Vector3 = hou.Vector3((parms['sx'], parms['sy'], parms['sz']))
        point.setAttribValue('scale', scale)
        point.setAttribValue('pscale', parms['uniform_scale'])

        self.updateGeometryData()
    # end setPointTransform

    @staticmethod
    def sopGeometryIntersection(geometry, ray_origin, ray_dir) -> tuple:
        """ Make objects for the intersect() method to modify. """
        position = hou.Vector3()
        normal = hou.Vector3()
        uvw = hou.Vector3()
        # Try intersecting the ray with the geometry
        intersected = geometry.intersect(
            ray_origin, ray_dir, position, normal, uvw
        )
        # Returns a tuple of four values:
        # - the primitive number of the primitive hit, or -1 if the ray didn't hit
        # - the 3D position of the intersection point (as Vector3)
        # - the normal of the ray to the hit primitive (as Vector3)
        # - the uvw coordinates of the intersection on the primitive (as Vector3)
        return (intersected, position, normal, uvw)
    # end sopGeometryIntersection
# end GeometryData