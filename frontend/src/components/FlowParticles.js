import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function FlowParticles({ start, end, count = 10, speed = 0.02 }) {
  const meshRef = useRef();
  
  // Create particle data
  const particles = useMemo(() => {
    const data = [];
    for (let i = 0; i < count; i++) {
      data.push({
        t: Math.random(), // initial position along the path (0 to 1)
        offset: new THREE.Vector3(
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 0.5
        ),
      });
    }
    return data;
  }, [count]);

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const startVec = useMemo(() => new THREE.Vector3(...start), [start]);
  const endVec = useMemo(() => new THREE.Vector3(...end), [end]);

  useFrame(() => {
    particles.forEach((particle, i) => {
      // Move particle forward
      particle.t += speed;
      if (particle.t > 1) particle.t = 0;

      // Calculate position along an arched path
      const pos = new THREE.Vector3().lerpVectors(startVec, endVec, particle.t);
      pos.y += Math.sin(particle.t * Math.PI) * 1.5; // Matches CurvedLine arch
      pos.add(particle.offset);

      dummy.position.copy(pos);
      dummy.scale.setScalar(0.1);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[null, null, count]}>
      <sphereGeometry args={[0.5, 8, 8]} />
      <meshStandardMaterial color="#06b6d4" emissive="#06b6d4" emissiveIntensity={5} transparent opacity={0.6} />
    </instancedMesh>
  );
}