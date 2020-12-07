
from app.ngs.project import GenericObject,projects,create_project,get_project
from app import databases


class SampleField(GenericObject):
    def delete(self,hard=False):
        if not hard:
            super().delete()
        else:
            f= self.data["field"]
            databases["system"].remove_columns("mev_samples",[f])
            super().delete(True)


projects["mev_sample_field"]=SampleField