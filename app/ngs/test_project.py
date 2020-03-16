from app.ngs.project import GenericObject,projects

class TestProject(GenericObject):
    def __init__(self,res):
        super().__init__(res=res)

projects["test_project"]=TestProject