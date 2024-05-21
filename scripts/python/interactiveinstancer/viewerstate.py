"""
State:          Interactive Instancer
State type:     aka::sopinteractiveinstancer::1.2
Description:    An artist friendly way of instancing via viewerstate
Author:         Amir Khaefi Ashkezari
Date Created:   May 12, 2024 - 23:43:07
"""

import hou
import viewerstate.utils as su
from enum import Enum


class GeometryParm:
    def __init__(self, node) -> None:
        self.node: hou.Node = node
        self.geometry: hou.Geometry = hou.Geometry()
        self.selection: hou.Selection = None

        self.initGeometry()
    # end __init__
        
    def initGeometry(self) -> None:
        geo_ptc_parm: hou.Parm = self.node.parm('geo_ptc')
        geo_ptc: hou.Geometry = geo_ptc_parm.evalAsGeometry()

        if geo_ptc:
            self.geometry.copy(geo_ptc)

        points = self.geometry.iterPoints()
        if not len(points):
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
        else:
            self.selection = hou.Selection((points[-1],))
    # end initGeometry
        
    def updateGeometryData(self) -> None:
        """ Replace geometry data parm with geometry property. 
        """
        self.node.parm('geo_ptc').set(self.geometry)
    # end updateGeometryData

    def getLastPoint(self) -> tuple[hou.Point, int]:
        """ Get the last point and it's id from the geometry. 
        """
        points = self.geometry.iterPoints()
        if not len(points):
            return (None, 0)

        last_pt = points[-1]
        return (last_pt, last_pt.attribValue('id'))
    # end getLastPoint
    
    def addPoint(self, position) -> None:
        """ generate a point and assign id. 
        """
        _, last_id = self.getLastPoint()
        last_pt = self.geometry.createPoint()
        last_pt.setPosition(position)
        last_pt.setAttribValue('id', last_id + 1)

        self.selection = hou.Selection((last_pt,))
        self.updateGeometryData()
    # end addPoint

    # def selectPoint(self, origin, direction) -> None:
    #     """ select the nearest point from position.
    #     """
    #     prim_num, _ = self.geometryIntersection(origin, direction)
    #     if prim_num < 0:
    #         return
    #     self.updateGeometryData()
    # # end selectPoint

    def setSelection(self, selection: hou.GeometrySelection) -> None:
        selection_str = selection.selectionStrings(
            empty_string_selects_all=False)
        if not selection_str:
            return

        self.selection = hou.Selection(
            self.geometry, hou.geometryType.Points, selection_str[0])

        self.updateGeometryData()
    # end setSelection

    def delete(self) -> None:
        sel_points = self.selection.points(self.geometry)
        if not sel_points:
            return

        self.geometry.deletePoints(sel_points)
        self.selection.clear()
        last_pt, _ = self.getLastPoint()
        if last_pt:
            self.selection = hou.Selection((last_pt,))

        self.updateGeometryData()
    # end delete

    def getPointTransform(self) -> tuple:
        """ Extract Point Transform. 
        """
        sel_points = self.selection.points(self.geometry)
        if not sel_points:
            return (hou.Vector3(), hou.Vector3(), hou.Vector3(), 0.0)

        last_pt = sel_points[-1]
        position = last_pt.position()
        rotation: hou.Vector3 = hou.Quaternion(
            last_pt.attribValue('orient')).extractEulerRotates()
        scale = hou.Vector3(last_pt.attribValue('scale'))
        uniformscale = last_pt.attribValue('pscale')

        return (position, rotation, scale, uniformscale)
    # end getPointTransform

    def setPointTransform(self, handle_kwargs: dict) -> None:
        """ Set Point Transform based on handle parms. 
        """
        parms = handle_kwargs['parms']
        prev_parms = handle_kwargs['prev_parms']

        sel_points = self.selection.points(self.geometry)
        if not sel_points:
            return

        last_pt = sel_points[-1]
        trn_delta = hou.Vector3((parms['tx'], parms['ty'], parms['tz'])) - \
            last_pt.position()
        inv_mtx: hou.Matrix3 = hou.Quaternion(
            last_pt.attribValue('orient')).extractRotationMatrix3().inverted()
        delta_mtx: hou.Matrix3 = hou.hmath.buildRotate(
            parms['rx'], parms['ry'], parms['rz']).extractRotationMatrix3()
        delta_mtx *= inv_mtx
        scale_delta = hou.Vector3((parms['sx'], parms['sy'], parms['sz'])) - \
            hou.Vector3(last_pt.attribValue('scale'))
        pscale_delta = parms['uniform_scale'] - last_pt.attribValue('pscale')

        tmp_mtx: hou.Matrix3 = hou.Matrix3()
        for sel_point in sel_points:
            sel_point.setPosition(sel_point.position() + trn_delta)
            rot_mtx: hou.Matrix3 = hou.Quaternion(
                sel_point.attribValue('orient')).extractRotationMatrix3()
            tmp_mtx.setToIdentity()
            tmp_mtx *= delta_mtx
            tmp_mtx *= rot_mtx
            orient = hou.Quaternion(tmp_mtx)
            sel_point.setAttribValue('orient', orient)
            scale = hou.Vector3(sel_point.attribValue('scale'))
            sel_point.setAttribValue('scale', scale + scale_delta)
            pscale = sel_point.attribValue('pscale')
            sel_point.setAttribValue('pscale', pscale + pscale_delta)

        self.updateGeometryData()
    # end setPointTransform

    def geometryIntersection(self, ray_origin, ray_dir) -> tuple:
        """ Make objects for the intersect() method to modify. """
        position = hou.Vector3()
        normal = hou.Vector3()
        uvw = hou.Vector3()
        bbox_geo = self.node.node('OUT_bbox').geometry()
        intersected = bbox_geo.intersect(
            ray_origin, ray_dir, position, normal, uvw
        )
        return (intersected, position)
    # end geometryIntersection
# end GeometryParm


class Mode(Enum):
    Create = 1
    Edit = 2
# end Mode


class State:
    MSG = 'LMB to add points to the construction plane.'

    def __init__(self, state_name, scene_viewer) -> None:
        self.state_name = state_name
        self.scene_viewer = scene_viewer

        self.mode = Mode.Create
        self.node: hou.Node = None
        self.gp: GeometryParm = None
        self.pressed = False

        self.xform_handle = hou.Handle(scene_viewer, 'xform_handle')
        self.xform_handle.update()
    # end __init__
                        
    def onEnter(self, kwargs) -> None:
        self.node = kwargs['node']
        if not self.node:
            raise
        
        self.gp = GeometryParm(self.node)
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
        """ Called when the state terminates. 
        """
        state_parms = kwargs['state_parms']
    # end onExit

    def start(self, origin, direction) -> None:
        if not self.pressed:
            self.scene_viewer.beginStateUndo('Add point')
            if self.mode == Mode.Create:
                position = su.cplaneIntersection(self.scene_viewer, origin, direction)
                self.gp.addPoint(position)
            elif self.mode == Mode.Edit:
                self.scene_viewer.triggerStateSelector(
                    hou.triggerSelectorAction.Start, name='selector_inst')

        self.pressed = True
    # end start

    def finish(self) -> None:
        if self.pressed:
            self.scene_viewer.endStateUndo()
        self.pressed = False
    # end finish
    
    def onMouseEvent(self, kwargs) -> bool:
        """ Find the position of the point to add by 
            intersecting the construction plane. 
        """
        ui_event = kwargs['ui_event']
        device = ui_event.device()
        origin, direction = ui_event.ray()
        
        if device.isLeftButton():
            self.start(origin, direction)
        else:
            self.finish()
                
        return False
    # end onMouseEvent

    def onMouseWheelEvent(self, kwargs) -> bool:
        """ Process a mouse wheel event.
        """
        ui_event = kwargs['ui_event']
        state_parms = kwargs['state_parms']

        # Must return True to consume the event
        return False
    
    def onKeyEvent(self, kwargs) -> bool:
        """ Find the position of the point to add by 
            intersecting the construction plane. 
        """
        ui_event = kwargs['ui_event']
        device = ui_event.device()
        
        if device.keyString() == 'f':
            self.mode = Mode.Create
        elif device.keyString() == 'g':
            self.mode = Mode.Edit
        elif device.keyString() == 'Del':
            self.gp.delete()
            return True

        return False
    # end onKeyEvent

    def onHandleToState(self, kwargs) -> None:
        """ Called when the user manipulates a handle.
        """
        handle_name = kwargs['handle']
        parms = kwargs['parms']
        prev_parms = kwargs['prev_parms']

        self.gp.setPointTransform(kwargs)
    # end onHandleToState

    def onStateToHandle(self, kwargs) -> None:
        """ Called when the user changes parameter(s), 
            so you can update dynamic handles if necessary
        """
        parms = kwargs["parms"]
        
        pos, rot, scale, uniformscale = self.gp.getPointTransform()
        parms['tx'], parms['ty'], parms['tz'] = pos.x(), pos.y(), pos.z()
        parms['rx'], parms['ry'], parms['rz'] = rot.x(), rot.y(), rot.z()
        parms['sx'], parms['sy'], parms['sz'] = scale.x(), scale.y(), scale.z()
        parms['uniform_scale'] = uniformscale
    # end onStateToHandle

    def onSelection(self, kwargs) -> bool:
        """ Called when a selector has selected something
        """
        selection = kwargs["selection"]
        state_parms = kwargs["state_parms"]

        self.gp.setSelection(selection)

        return False
    # end onSelection
# end State