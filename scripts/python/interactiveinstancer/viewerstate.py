"""
State:          Interactive Instancer
State type:     aka::sopinteractiveinstancer::1.2
Description:    An artist friendly way of instancing via viewerstate
Author:         Amir Khaefi Ashkezari
Date Created:   May 12, 2024 - 23:43:07
"""

import hou
import viewerstate.utils as su
import nodegeo as ng


class State:
    MSG = 'LMB to add points to the construction plane.'

    def __init__(self, state_name, scene_viewer) -> None:
        self.state_name = state_name
        self.scene_viewer = scene_viewer

        self.node: hou.Node = None
        self.gd: ng.GeometryData = None
        self.pressed = False

        self.xform_handle = hou.Handle(scene_viewer, 'xform_handle')
        self.xform_handle.update()
    # end __init__
                        
    def onEnter(self, kwargs) -> None:
        self.node = kwargs['node']
        if not self.node:
            raise
        
        self.gd = ng.GeometryData(self.node)
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

    def start(self, position) -> None:
        if not self.pressed:
            self.scene_viewer.beginStateUndo('Add point')
            self.gd.genPointcloud(position)

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
        """ Process a mouse wheel event.
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
        """ Called when the user manipulates a handle.
        """
        handle_name = kwargs['handle']
        parms = kwargs['parms']
        prev_parms = kwargs['prev_parms']

        last_pt, _ = self.gd.getLastPoint()
        if not last_pt:
            return

        self.gd.setPointTransform(parms, last_pt)
    # end onHandleToState

    def onStateToHandle(self, kwargs) -> None:
        """ Called when the user changes parameter(s), 
            so you can update dynamic handles if necessary
        """
        parms = kwargs["parms"]

        last_pt, _ = self.getLastPoint()
        if not last_pt:
            return
        
        pos, rot, scale, uniformscale = self.gd.getPointTransform(last_pt)
        parms['tx'], parms['ty'], parms['tz'] = pos.x(), pos.y(), pos.z()
        parms['rx'], parms['ry'], parms['rz'] = rot.x(), rot.y(), rot.z()
        parms['sx'], parms['sy'], parms['sz'] = scale.x(), scale.y(), scale.z()
        parms['uniform_scale'] = uniformscale
    # end onStateToHandle

    def onEndHandleToState(self, kwargs) -> None:
        handle_name = kwargs["handle"]
        ui_event = kwargs["ui_event"]
    # end onEndHandleToState
# end State