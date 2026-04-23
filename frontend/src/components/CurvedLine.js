import * as THREE from "three";

export default function CurvedLine({ start, end, color = "#ffffff", opacity = 0.2 }) {
  const points = [];
  const startVec = new THREE.Vector3(...start);
  const endVec = new THREE.Vector3(...end);
  
  // Create an arched path
  for (let i = 0; i <= 20; i++) {
    const t = i / 20;
    const p = new THREE.Vector3().lerpVectors(startVec, endVec, t);
    p.y += Math.sin(t * Math.PI) * 2; // The arch height
    points.push(p);
  }

  const curve = new THREE.CatmullRomCurve3(points);
  const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(50));

  return (
    <line geometry={geometry}>
      <lineBasicMaterial color={color} transparent opacity={opacity} />
    </line>
  );
}