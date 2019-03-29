class TuioTrackingInfo(object):
    def __init__(self, **kwargs):
        self.matching_resource = ""
        if "matching_resource" in kwargs:
            self.matching_resource = kwargs["matching_resource"]
        self.varying_upload_resource = ""
        if "varying_upload_resource" in kwargs:
            self.varying_upload_resource = kwargs["varying_upload_resource"]
        self.matching_scale = -1.0
        if "matching_scale" in kwargs:
            self.matching_scale = float(kwargs["matching_scale"])
        self.fixed_resource_scale = []
        if "fixed_resource_scale" in kwargs:
            self.fixed_resource_scale = kwargs["fixed_resource_scale"]
