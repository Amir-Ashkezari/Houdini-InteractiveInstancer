"""
State:          Interactive Instancer
State type:     aka::sopinteractiveinstancer::1.2
Description:    An artist friendly way of instancing via viewerstate
Author:         Amir Khaefi Ashkezari
Date Created:   May 12, 2024 - 23:43:07
"""

import hou
import viewerstate.utils as su


class State:
    MSG = 'LMB to add points to the construction plane.'

    xform_parm_pairs = {
    'tx': 't_x', 'ty': 't_y', 'tz': 't_z',
    'rx': 'r_x', 'ry': 'r_y', 'rz': 'r_z',
    'sx': 's_x', 'sy': 's_y', 'sz': 's_z',
    'uniform_scale': 'uniformscale_'
    }

    def __init__(self, state_name, scene_viewer) -> None:
        self.state_name = state_name
        self.scene_viewer = scene_viewer

        self.node: hou.Node = None
        self._geometry: hou.Geometry = hou.Geometry()
        self.pressed = False

        self.xform_handle = hou.Handle(scene_viewer, 'xform_handle')
        self.xform_handle.update()
    # end __init__
        
    def initGeometry(self) -> None:
        geo_ptc_parm: hou.Parm = self.node.parm('geo_ptc')
        geo_ptc: hou.Geometry = geo_ptc_parm.evalAsGeometry()

        if geo_ptc:
            self._geometry.copy(geo_ptc)

        if not self._geometry.points():
            orient_attrib: hou.Attrib = self._geometry.addAttrib(
                hou.attribType.Point, 'orient', [0.0, 0.0, 0.0, 0.0])
            scale_attrib: hou.Attrib = self._geometry.addAttrib(
                hou.attribType.Point, 'scale', [1.0, 1.0, 1.0])
            pscale_attrib: hou.Attrib = self._geometry.addAttrib(
                hou.attribType.Point, 'pscale', 1.0)
            id_attrib: hou.Attrib = self._geometry.addAttrib(
                hou.attribType.Point, 'id', 0)
            orient_attrib.setOption('type', 'quaternion')
            scale_attrib.setOption('type', 'vector')
            pscale_attrib.setOption('type', 'float')
            id_attrib.setOption('type', 'int')
    # end initGeometry
                
    def onEnter(self, kwargs) -> None:
        self.node = kwargs['node']
        if not self.node:
            raise
        
        self.initGeometry() 
        self.scene_viewer.setPromptMessage(State.MSG)
    # end onEnter

    def onInterrupt(self, kwargs) -> None:
        self.xform_handle.show(False)
        self.finish()
    # end onInterrupt

    def onResume(self, kwargs) -> None:
        self.xform_handle.show(True)
        self.scene_viewer.setPromptMessage(State.MSG)
    # end onResume

    def onExit(self,kwargs) -> None:
        """ Called when the state terminates
        """
        state_parms = kwargs['state_parms']
    # end onExit

    def getLastPoint(self) -> tuple[hou.Point, int]:
        """ Reterive the last point and it's id from the geometry. 
        """
        geo_ptc: hou.Geometry = self.node.parm('geo_ptc').evalAsGeometry()
        if geo_ptc and geo_ptc.points():
            last_pt: hou.Point = geo_ptc.iterPoints()[-1]
            last_id = last_pt.attribValue('id')
            return (last_pt, last_id)

        return (None, 0)
    # end getLastPoint

    def start(self, position) -> None:
        if not self.pressed:
            self.scene_viewer.beginStateUndo('Add point')
            self.genPointcloud(position)

        self.pressed = True
    # end start

    def finish(self) -> None:
        if self.pressed:
            self.scene_viewer.endStateUndo()
        self.pressed = False
    # end finish
    
    def genPointcloud(self, position) -> None:
        """ generate a point and assign id
        """
        _, last_id = self.getLastPoint()
        pt: hou.Point = self._geometry.createPoint()
        pt.setPosition(position)
        pt.setAttribValue('id', last_id + 1)

        self.node.parm('geo_ptc').set(self._geometry)
    # end genPointcloud

    def onMouseEvent(self, kwargs) -> bool:
        """ Find the position of the point to add by 
            intersecting the construction plane. 
        """
        ui_event = kwargs['ui_event']
        device = ui_event.device()
        origin, direction = ui_event.ray()
        
        position = su.cplaneIntersection(self.scene_viewer, origin, direction)
           
        # Create/move point if LMB is down
        if device.isLeftButton():
            if device.isCtrlKey():
                print('ctrl')
            else:
                self.start(position)
        else:
            self.finish()
            
        return True
    # end onMouseEvent

    def onMouseWheelEvent(self, kwargs) -> bool:
        """ Process a mouse wheel event
        """
        ui_event = kwargs['ui_event']
        state_parms = kwargs['state_parms']

        # Must return True to consume the event
        return False
    
    def onBeginHandleToState(self, kwargs) -> None:
        handle_name = kwargs["handle"]
        ui_event = kwargs["ui_event"]
    # end onBeginHandleToState

    def onHandleToState(self, kwargs) -> None:
        # Called when the user manipulates a handle
        handle_name = kwargs['handle']
        parms = kwargs['parms']
        prev_parms = kwargs['prev_parms']

        # for parm_name in kwargs['mod_parms']:
        #     old_value = prev_parms[parm_name]
        #     new_value = parms[parm_name]
        #     print(new_value)
        #     print("%s was: %s now: %s" % (parm_name, old_value, new_value))

        point: hou.Point = self.getLastPoint()
        if not point:
            return
        
        # for key, value in State.xform_parm_pairs.items():
        #     parm_name = value.replace('_', str(points))
        #     self.node.parm(parm_name).set(parms[key])
    # end onHandleToState

    def onStateToHandle(self, kwargs) -> None:
        # Called when the user changes parameter(s), so you can update
        # dynamic handles if necessary
        parms = kwargs["parms"]

        # pt = self.getLastPoint()
        # if not pt:
        #     return

        # for key, value in State.xform_parm_pairs.items():
        #     parm_name = value.replace('_', str(points))
        #     parms[key] = self.node.parm(parm_name).eval()
    # end onStateToHandle

    def onEndHandleToState(self, kwargs) -> None:
        handle_name = kwargs["handle"]
        ui_event = kwargs["ui_event"]
    # end onEndHandleToState
        
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
# end State