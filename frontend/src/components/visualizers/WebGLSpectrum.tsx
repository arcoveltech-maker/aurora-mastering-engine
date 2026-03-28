import { useEffect, useRef } from 'react';

interface Props {
  analyser?: AnalyserNode | null;
  width?: number;
  height?: number;
  color?: string;
}

const VERT_SRC = `
attribute vec2 a_position;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}`;

const FRAG_SRC = `
precision mediump float;
uniform vec4 u_color;
void main() {
  gl_FragColor = u_color;
}`;

function compileShader(gl: WebGLRenderingContext, type: number, src: string) {
  const sh = gl.createShader(type)!;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  return sh;
}

export function WebGLSpectrum({ analyser, width = 512, height = 120, color = '#9dff7c' }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef     = useRef<WebGLRenderingContext | null>(null);
  const progRef   = useRef<WebGLProgram | null>(null);
  const rafRef    = useRef<number>(0);

  // Parse colour to RGBA
  const parseColor = (hex: string): [number, number, number, number] => {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    return [r, g, b, 1.0];
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl');
    if (!gl) return;
    glRef.current = gl;

    const vert = compileShader(gl, gl.VERTEX_SHADER, VERT_SRC);
    const frag = compileShader(gl, gl.FRAGMENT_SHADER, FRAG_SRC);
    const prog = gl.createProgram()!;
    gl.attachShader(prog, vert);
    gl.attachShader(prog, frag);
    gl.linkProgram(prog);
    gl.useProgram(prog);
    progRef.current = prog;

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);

    const posLoc = gl.getAttribLocation(prog, 'a_position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    gl.clearColor(0.067, 0.075, 0.094, 1.0);

    const fftSize = analyser?.frequencyBinCount ?? 256;
    const freqData = new Uint8Array(fftSize);

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw);
      if (analyser) analyser.getByteFrequencyData(freqData);

      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.viewport(0, 0, canvas.width, canvas.height);

      const rgba = parseColor(color);
      const uColor = gl.getUniformLocation(prog, 'u_color');
      gl.uniform4fv(uColor, rgba);

      const n = freqData.length;
      const verts: number[] = [];
      for (let i = 0; i < n; ++i) {
        const x = (i / n) * 2 - 1;
        const x2 = ((i + 1) / n) * 2 - 1;
        const y = analyser ? (freqData[i] / 255) * 2 - 1 : (Math.random() * 0.3 - 1);
        verts.push(x, -1, x2, -1, x, y, x2, -1, x2, y, x, y);
      }

      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.DYNAMIC_DRAW);
      gl.drawArrays(gl.TRIANGLES, 0, verts.length / 2);
    };
    draw();

    return () => {
      cancelAnimationFrame(rafRef.current);
      gl.deleteProgram(prog);
    };
  }, [analyser, color]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ width: '100%', height, display: 'block', borderRadius: 3 }}
    />
  );
}
