import bpy
import math
from itertools import zip_longest
from mathutils import Vector


from src.utils.data_utils import get_data_as_ll, find_data_range, find_axis_range, normalize_value, get_data_in_range
from src.operators.features.axis import AxisFactory
from src.general import OBJECT_OT_generic_chart
from src.general import CONST


class OBJECT_OT_line_chart(OBJECT_OT_generic_chart):
    '''Creates line chart as a line or as curve'''
    bl_idname = 'object.create_line_chart'
    bl_label = 'Line Chart'
    bl_options = {'REGISTER', 'UNDO'}

    rounded: bpy.props.EnumProperty(
        name='Rounded',
        items=(
            ('1', 'Rounded', 'Beveled corners'),
            ('2', 'Sharp', 'Sharp corners')
        )
    )
    auto_ranges: bpy.props.BoolProperty(
        name='Automatic axis ranges',
        default=True
    )

    x_axis_step: bpy.props.FloatProperty(
        name='Step of x axis',
        default=1.0
    )

    x_axis_range: bpy.props.FloatVectorProperty(
        name='Range of x axis',
        size=2,
        default=(0.0, 1.0)
    )

    z_axis_step: bpy.props.FloatProperty(
        name='Step of z axis',
        default=1.0
    )

    padding: bpy.props.FloatProperty(
        name='Padding',
        default=0.1,
        min=0.0
    )

    def __init__(self):
        self.cuver_obj = None
        self.only_2d = True
        self.x_delta = 0.2
        self.bevel_obj_size = (0.01, 0.01, 0.01)
        self.bevel_settings = {
            'rounded': {
                'segments': 5,
                'offset': 0.05,
                'profile': 0.6,
            },
            'sharp': {
                'segments': 3,
                'offset': 0.02,
                'profile': 1.0,
            },
        }

    def draw(self, context):
        super().draw(context)

    def execute(self, context):
        self.init_data()
        self.create_container()

        data_list = get_data_as_ll(self.data)
        if len(data_list[0]) > 2:
            self.report({'ERROR'}, 'Line chart supports X Y values only')
            return {'CANCELLED'}
        
        if self.auto_ranges:
            self.x_axis_range = find_axis_range(data_list, 0)
        
        data_min, data_max = find_data_range(data_list, self.x_axis_range)

        data_list = get_data_in_range(data_list, self.x_axis_range)

        sorted_data = sorted(data_list, key=lambda x: x[0])

        normalized_vert_list = [(normalize_value(entry[0], self.x_axis_range[0], self.x_axis_range[1]), 0.0, normalize_value(entry[1], data_min, data_max)) for entry in sorted_data]
        edges = [[i - 1, i] for i in range(1, len(normalized_vert_list))]

        self.create_curve(normalized_vert_list, edges)
        self.add_bevel_obj()

        AxisFactory.create(
            self.container_object,
            (self.x_axis_step, 0, self.z_axis_step),
            (self.x_axis_range, [], (data_min, data_max)),
            2,
            padding=self.padding,
            offset=0.0
        )
        return {'FINISHED'}
        
    def create_curve(self, verts, edges):
        m = bpy.data.meshes.new('line_mesh')
        self.curve_obj = bpy.data.objects.new('curve_obj', m)

        bpy.context.scene.collection.objects.link(self.curve_obj)
        self.curve_obj.parent = self.container_object
        m.from_pydata(verts, edges, [])
        m.update()

        self.select_curve_obj()
        
        self.bevel_curve_obj()

        bpy.ops.object.convert(target='CURVE')

    def bevel_curve_obj(self):
        bpy.ops.object.mode_set(mode='EDIT')
        opts = self.bevel_settings['rounded'] if self.rounded == '1' else self.bevel_settings['sharp']
        bpy.ops.mesh.bevel(
            segments=opts['segments'], 
            offset=opts['offset'], 
            offset_type='OFFSET',
            profile=opts['profile'],
            vertex_only=True
        )   
        bpy.ops.object.mode_set(mode='OBJECT')

    def add_bevel_obj(self):
        bpy.ops.mesh.primitive_plane_add()
        bevel_obj = bpy.context.active_object
        bevel_obj.scale = self.bevel_obj_size
        
        bpy.ops.object.convert(target='CURVE')
        self.curve_obj.data.bevel_object = bevel_obj
        return bevel_obj

    def select_curve_obj(self):
        self.curve_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.curve_obj
