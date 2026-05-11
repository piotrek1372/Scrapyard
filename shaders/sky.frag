#version 330

/**
 * Equirectangular fragment shader for HDR Skybox.
 * Maps world-space direction to equirectangular UVs.
 */

uniform sampler2D p3d_Texture0; // The HDR texture
in vec3 v_dir;                 // World-space direction from vertex shader
out vec4 p3d_FragColor;

const float PI = 3.14159265359;

void main() {
    vec3 d = normalize(v_dir);
    
    // Equirectangular mapping formula
    // atan(z, x) gives longitude, asin(y) gives latitude
    vec2 uv = vec2(
        atan(d.z, d.x) / (2.0 * PI) + 0.5,
        asin(clamp(d.y, -1.0, 1.0)) / PI + 0.5
    );
    
    vec3 hdr_color = texture(p3d_Texture0, uv).rgb;
    
    // Reinhard Tone Mapping for visual balance
    vec3 mapped = hdr_color / (hdr_color + vec3(1.0));
    
    // Gamma correction (sRGB)
    mapped = pow(mapped, vec3(1.0 / 2.2));
    
    p3d_FragColor = vec4(mapped, 1.0);
}
