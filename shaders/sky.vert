#version 330

/**
 * Simple vertex shader for Skybox.
 * Passes the vertex position as world-space direction.
 */

uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
out vec3 v_dir;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    // The vertex position on the sphere is the direction from the center
    v_dir = p3d_Vertex.xyz;
}
