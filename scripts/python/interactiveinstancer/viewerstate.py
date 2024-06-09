"""
State:          Interactive Instancer
State type:     aka::sopinteractiveinstancer::1.2
Description:    An artist friendly way of instancing via viewerstate
Author:         Amir Khaefi Ashkezari
Date Created:   May 12, 2024 - 23:43:07
"""

import hou
import viewerstate.utils as su
import viewerhandle.utils as hu
from enum import Enum
from dataclasses import dataclass


@dataclass
class XformInfo:
    position: hou.Vector3 = hou.Vector3()
    rotation: hou.Vector3 = hou.Vector3()
    scale: hou.Vector3 = hou.Vector3(1.0, 1.0, 1.0)
    uniform_scale: float = 1.0

@dataclass
class RayInfo:
    hitprim: int = -1
    hitpos: hou.Vector3 = hou.Vector3()
    hitnormal: hou.Vector3 = hou.Vector3()
    hituvw: hou.Vector3 = hou.Vector3()

@dataclass
class PrimUV:
    prim: hou.Prim = None
    u: float = 0.0
    v: float = 0.0
    dist: float = 0.0

    @classmethod
    def from_tuple(cls, data):
        return cls(data[0], data[1], data[2], data[3])


class GeometryParm:
    def __init__(self, node) -> None:
        self.node: hou.Node = node
        self.geometry: hou.Geometry = hou.Geometry()
        self.ray_geo: hou.Geometry = hou.Geometry()
        self.selection: hou.Selection = None

        self.initGeometry()
    # end __init__

    def initGeometry(self) -> None:
        geo_ptc_parm: hou.Parm = self.node.parm('geo_ptc')
        geo_ptc: hou.Geometry = geo_ptc_parm.evalAsGeometry()

        if geo_ptc:
            self.geometry.copy(geo_ptc)

        points = self.geometry.iterPoints()
        if not points:
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

        self.isGuideValid()
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
        if not points:
            return (None, 0)

        last_pt = points[-1]
        return (last_pt, last_pt.attribValue('id'))
    # end getLastPoint
    
    def addPoint(self, xform_info: XformInfo) -> None:
        """ generate a point and assign id. 
        """
        _, last_id = self.getLastPoint()
        last_pt = self.geometry.createPoint()
        last_pt.setPosition(xform_info.position)
        last_pt.setAttribValue('id', last_id + 1)

        self.selection = hou.Selection((last_pt,))
        self.updateGeometryData()
    # end addPoint

    def getSelection(self) -> tuple[hou.Point]:
        if not self.selection:
            return None
        return self.selection.points(self.geometry)
    # end getSelection

    def setSelection(self, selection: hou.GeometrySelection) -> None:
        selection_str = selection.selectionStrings(
            empty_string_selects_all=False)
        if selection_str:
            self.selection = hou.Selection(
                self.geometry, hou.geometryType.Points, selection_str[0])
        else:
            self.selection = None

        self.updateGeometryData()
    # end setSelection

    def delete(self) -> None:
        points = self.getSelection()
        if not points:
            return

        self.geometry.deletePoints(points)
        self.selection = None

        self.updateGeometryData()
    # end delete

    def getPointTransform(self) -> XformInfo:
        """ Extract Point Transform. 
        """
        xform_info = XformInfo()
        points = self.getSelection()
        if not points:
            return xform_info

        last_pt = points[-1]
        xform_info.position = last_pt.position()
        xform_info.rotation = hou.Quaternion(
            last_pt.attribValue('orient')).extractEulerRotates()
        xform_info.scale = hou.Vector3(last_pt.attribValue('scale'))
        xform_info.uniform_scale = last_pt.attribValue('pscale')

        return xform_info
    # end getPointTransform

    def isGuideValid(self) -> bool:
        input_geo: hou.Geometry = self.node.node('GUIDE').geometry()
        contain_polygon =  input_geo.containsPrimType(hou.primType.Polygon)
        if contain_polygon and input_geo.iterPrims():
            self.ray_geo.copy(input_geo)
            return True
            
        self.ray_geo.clear()            
        return False
    # end isGuideValid

    def intersect(self, ray_origin, ray_dir) -> RayInfo:
        """ Make objects for the intersect() method to modify. """
        ray_info = RayInfo()
        ray_info.hitprim = self.ray_geo.intersect(
            ray_origin, ray_dir, 
            ray_info.hitpos, ray_info.hitnormal, ray_info.hituvw
        )
        return ray_info
    # end intersect

    def minPos(self, xform_info: XformInfo) -> None:
        """ Find the nearset prim pos in Guide geo.
        """
        primuv: PrimUV = PrimUV.from_tuple(
            self.ray_geo.nearestPrim(xform_info.position))
        if not primuv.prim:
            return
        
        real_uv_coords = hou.Vector2(primuv.u, primuv.v)
        unit_coords = primuv.prim.primuvConvert(real_uv_coords, 0)
        xform_info.position = primuv.prim.positionAtInterior(
            unit_coords.x(), unit_coords.y())
    # end minPos

    def setPointTransform(self, xform_info: XformInfo) -> None:
        """ Set Point Transform based on handle parms. 
        """
        points = self.getSelection()
        if not points:
            return

        delta_info = XformInfo()
        last_pt = points[-1]
        delta_info.position =  xform_info.position - last_pt.position()
        delta_mtx: hou.Matrix3= hou.hmath.buildRotate(
            xform_info.rotation).extractRotationMatrix3()
        delta_mtx *= hou.Quaternion(
            last_pt.attribValue('orient')).extractRotationMatrix3().inverted()
        delta_info.scale = xform_info.scale - \
            hou.Vector3(last_pt.attribValue('scale'))
        delta_info.uniform_scale = xform_info.uniform_scale - \
            last_pt.attribValue('pscale')

        tmp_mtx: hou.Matrix3 = hou.Matrix3()
        for point in points:
            point.setPosition(point.position() + delta_info.position)
            rot_mtx: hou.Matrix3 = hou.Quaternion(
                point.attribValue('orient')).extractRotationMatrix3()
            tmp_mtx.setToIdentity()
            tmp_mtx *= delta_mtx
            tmp_mtx *= rot_mtx
            orient = hou.Quaternion(tmp_mtx)
            point.setAttribValue('orient', orient)
            scale = hou.Vector3(point.attribValue('scale'))
            point.setAttribValue('scale', scale + delta_info.scale)
            pscale = point.attribValue('pscale')
            point.setAttribValue('pscale', pscale + delta_info.uniform_scale)

        self.updateGeometryData()
    # end setPointTransform

    def snapToGuide(self, xform_info) -> None:
        """ Find the minimum position from guide 
            and snap the point onto it.
        """
        points = self.getSelection()
        if not points:
            return
        
        self.minPos(xform_info)
    # end snapToGuide
# end GeometryParm


class Mode(Enum):
    SingleCreate = 1
    BrushCreate = 2
    Edit = 3
# end Mode


class State:
    MSG = 'Add an instance.'

    def __init__(self, state_name, scene_viewer) -> None:
        self.state_name = state_name
        self.scene_viewer: hou.SceneViewer = scene_viewer

        self.mode = Mode.SingleCreate
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
        self.finish()
    # end onInterrupt

    def onResume(self, kwargs) -> None:
        self.gp.isGuideValid()
        self.scene_viewer.setPromptMessage(State.MSG)
    # end onResume

    def onExit(self,kwargs) -> None:
        """ Called when the state terminates. 
        """
        state_parms = kwargs['state_parms']
    # end onExit

    def start(self, xform_info: XformInfo) -> None:
        if not self.pressed:
            self.scene_viewer.beginStateUndo('add')
            if self.mode == Mode.SingleCreate:
                self.gp.addPoint(xform_info)
            elif self.mode == Mode.BrushCreate:
                # TODO 
                pass
            elif self.mode == Mode.Edit:
                # TODO 
                pass

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
        ui_event: hou.ViewerEvent = kwargs['ui_event']
        reason: hou.uiEventReason = ui_event.reason()
        device: hou.UIEventDevice = ui_event.device()
        consumed = False

        if device.isLeftButton():
            ray_origin, ray_dir = ui_event.ray()

            xform_info = XformInfo()
            succeed = self.gp.isGuideValid()
            if self.node.parm('enable_guide') and succeed:
                ray_info: RayInfo = self.gp.intersect(ray_origin, ray_dir)
                if ray_info.hitprim < 0:
                    return consumed
                xform_info.position = ray_info.hitpos
            else:
                xform_info.position = su.cplaneIntersection(
                    self.scene_viewer, ray_origin, ray_dir)

            self.start(xform_info)
            if self.mode != Mode.BrushCreate and \
                reason == hou.uiEventReason.Active:
                self.gp.setPointTransform(xform_info)
        else:
            self.finish()
                
        return consumed
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
        ui_event: hou.ViewerEvent = kwargs['ui_event']
        device = ui_event.device()
        consumed = False

        if device.keyString() == 'f':
            State.MSG = 'Add an instance.'
            self.scene_viewer.triggerStateSelector(
                    hou.triggerSelectorAction.Stop, name='selector_inst')
            self.mode = Mode.SingleCreate
            consumed = True
        elif device.keyString() == 'b':
            State.MSG = 'Paint instances base on the brush settings.'
            self.scene_viewer.triggerStateSelector(
                    hou.triggerSelectorAction.Stop, name='selector_inst')
            consumed = True
        elif device.keyString() == 'g':
            State.MSG = 'Select instance(s) to edit.'
            self.scene_viewer.triggerStateSelector(
                    hou.triggerSelectorAction.Start, name='selector_inst')
            self.mode = Mode.Edit
            consumed = True
        elif device.keyString() == 'Del':
            self.gp.delete()
            self.scene_viewer.curViewport().draw()
            consumed = True

        self.scene_viewer.setPromptMessage(State.MSG)
        return consumed
    # end onKeyEvent

    def onBeginHandleToState(self, kwargs) -> None:
        handle_name = kwargs['handle']
        ui_event = kwargs['ui_event']
        
        self.scene_viewer
        self.scene_viewer.beginStateUndo('editing')
    # end onBeginHandleToState

    def onStateToHandle(self, kwargs) -> None:
        """ Called when the user changes parameter(s), 
            so you can update dynamic handles if necessary
        """
        parms = kwargs['parms']

        self.log(kwargs)

        if not self.gp.selection:
            self.xform_handle.show(False)
            self.xform_handle.update()
            return

        self.xform_handle.show(True)

        xform_info = self.gp.getPointTransform()
        parms['tx'] = xform_info.position.x()
        parms['ty'] = xform_info.position.y()
        parms['tz'] = xform_info.position.z()
        parms['rx'] = xform_info.rotation.x()
        parms['ry'] = xform_info.rotation.y()
        parms['rz'] = xform_info.rotation.z()
        parms['sx'] = xform_info.scale.x()
        parms['sy'] = xform_info.scale.y()
        parms['sz'] = xform_info.scale.z()
        parms['uniform_scale'] = xform_info.uniform_scale

        self.xform_handle.update()
    # end onStateToHandle

    def onHandleToState(self, kwargs) -> None:
        """ Called when the user manipulates a handle.
        """
        handle_name = kwargs['handle']
        parms = kwargs['parms']
        prev_parms = kwargs['prev_parms']
        ui_event = kwargs['ui_event']
        
        xform_info = XformInfo()
        xform_info.position = hou.Vector3(
            (parms['tx'], parms['ty'], parms['tz']))
        xform_info.rotation = hou.Vector3(
            (parms['rx'], parms['ry'], parms['rz']))
        xform_info.scale = hou.Vector3(
            (parms['sx'], parms['sy'], parms['sz'])) 
        xform_info.uniform_scale = parms['uniform_scale']

        if self.node.parm('enable_guide'):
            self.gp.snapToGuide(xform_info)
            
        self.gp.setPointTransform(xform_info)
        self.xform_handle.update()
    # end onHandleToState

    def onEndHandleToState(self, kwargs) -> None:
        handle_name = kwargs['handle']
        ui_event = kwargs['ui_event']

        self.scene_viewer.endStateUndo()
    # end onEndHandleToState

    def onSelection(self, kwargs) -> bool:
        """ Called when a selector has selected something
        """
        selection = kwargs["selection"]
        state_parms = kwargs["state_parms"]

        self.gp.setSelection(selection)
        self.setHandleVisibility()

        return False
    # end onSelection

    def setHandleVisibility(self) -> bool:
        visiblity = True if self.gp.selection else False
        self.xform_handle.show(visiblity)
        self.xform_handle.update()
        return visiblity
    # end setHandleVisibility
# end State