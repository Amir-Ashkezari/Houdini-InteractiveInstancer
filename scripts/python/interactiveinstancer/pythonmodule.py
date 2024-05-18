"""
InteractiveInstancer Python Module
"""

import hou


def clearInstances(kwargs) -> None:
    node = kwargs['node']
    choice = hou.ui.displayConfirmation('Are you sure you want to remove all the instance?', 
        severity=hou.severityType.Warning, title='sopviewerinstancer cleanup')
    if choice:
        node.parm('geo_ptc').set(hou.Geometry())
# end clearInstances