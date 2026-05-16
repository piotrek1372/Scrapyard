#version 120

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform float osg_FrameTime;

attribute vec4 p3d_Vertex;
attribute vec2 p3d_MultiTexCoord0;

varying vec2 v_texcoord;
varying float v_height;
varying vec3 v_world_pos;

void main() {
    v_texcoord = p3d_MultiTexCoord0;
    
    vec4 world_pos = p3d_ModelMatrix * p3d_Vertex;
    
    // Radial wave calculation (parallel to shore)
    float dist = length(world_pos.xy);
    float time = osg_FrameTime * 1.5;
    
    // Wave 1: Main radial surge
    float wave1 = sin(dist * 0.4 - time) * 0.15;
    // Wave 2: Smaller cross-ripples for variety
    float wave2 = cos(dist * 0.8 + time * 0.5) * 0.05;
    
    float height = wave1 + wave2;
    v_height = height;
    
    vec4 v = p3d_Vertex;
    v.z += height;
    
    v_world_pos = (p3d_ModelMatrix * v).xyz;
    gl_Position = p3d_ModelViewProjectionMatrix * v;
}
