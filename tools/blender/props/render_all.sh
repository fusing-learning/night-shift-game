#!/bin/bash
# Usage: render_all.sh [glb]  -> previews in tools/blender/props/previews
cd "$(dirname "$0")/../../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
GLB=${1:-public/models/props.glb}
OUT=tools/blender/props/previews
mkdir -p $OUT
r() { # name names view cols res
  $B -b --python tools/blender/props/render_previews.py -- --glb $GLB --names $2 --view $3 --cols $4 --res ${5:-1600x1000} --out $PWD/$OUT/$1_$3.png 2>&1 | grep -E "Traceback|Error" ; }
G1=crate_metal,crate_small,crate_stack,pallet,barrel,barrel_tipped,gas_cylinder,bucket,toolbox,cone,body_bag,debris_a,debris_b,debris_c
G2=cart,forklift,workbench,shelf_rack,locker_row,ladder
G3=pipe_straight,pipe_elbow,pipe_valve,pipe_vertical,pipe_bundle,duct
G4=vent_fan,cable_floor_a,cable_floor_b,cable_floor_c,cable_coil,cable_hanging,chain_hook
G5=conveyor,conveyor_end,machine_a,machine_b,control_console,generator
G6=tank_vertical,tank_horizontal,crucible,pillar,railing,lamp_hanging
G7=lamp_wall,lamp_work,electrical_box,keycard_reader,door_shutter,pickup_energy,pickup_health,pickup_key,wall_vent,wall_sign,wall_fusebox
for v in game 3q; do
  r sheet1_clutter $G1 $v 5
  r sheet2_big_props $G2 $v 3
  r sheet3_pipes $G3 $v 3
  r sheet4_cables $G4 $v 4
  r sheet5_machines $G5 $v 3
  r sheet6_tanks $G6 $v 3
  r sheet7_small $G7 $v 4
  for h in machine_press furnace door_frame forklift; do r hero_$h $h $v 1 1200x900; done
done
