#version 120

varying vec2 v_texcoord;
varying float v_height;
varying vec3 v_world_pos;

uniform float osg_FrameTime;

void main() {
    // Base water color (dark teal)
    vec3 water_color = vec3(0.1, 0.18, 0.28);
    
    // Highlight based on wave height
    float highlight = smoothstep(0.05, 0.2, v_height);
    water_color += vec3(0.1, 0.15, 0.2) * highlight;
    
    // Refined ripples with more frequency
    float ripples = sin(v_world_pos.x * 8.0 + osg_FrameTime) * 
                    cos(v_world_pos.y * 8.0 - osg_FrameTime * 0.5) *
                    sin((v_world_pos.x + v_world_pos.y) * 5.0 + osg_FrameTime * 1.2);
    
    if (ripples > 0.8) {
        water_color += vec3(0.2, 0.25, 0.3) * (ripples - 0.8) * 5.0;
    }
    
    gl_FragColor = vec4(water_color, 1.0);
}
