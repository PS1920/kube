import React, { useRef } from "react";
import { Text, Float } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";

export default function Node({ position, status, label, onClick }) {
  const meshRef = useRef();
  
  let color = "#10b981"; // healthy (green)
  if (status === "recovering") color = "#facc15"; // yellow
  if (status === "degraded") color = "#fb923c"; // orange
  if (status === "failure") color = "#f43f5e"; // red

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.rotation.y = t * 0.5;
      
      if (status === "recovering") {
        // Yellow pulse effect for self-healing/recovering
        meshRef.current.material.emissiveIntensity = 1.5 + Math.sin(t * 2) * 1.0;
      } else if (status === "degraded") {
        // Slow flickering orange for long-term partial failure
        meshRef.current.material.emissiveIntensity = 1.2 + Math.sin(t * 1.5) * 0.8;
      } else if (status === "failure") {
        // Fast aggressive red blinking for actual errors
        meshRef.current.material.emissiveIntensity = 2 + Math.sin(t * 8) * 2;
      } else {
        // Stable
        meshRef.current.material.emissiveIntensity = 1.5;
      }
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.5} position={position}>
      <group onClick={onClick}>
        <mesh ref={meshRef}>
          <icosahedronGeometry args={[0.7, 1]} />
          <meshStandardMaterial 
            color={color} 
            emissive={color} 
            emissiveIntensity={1.5} 
            wireframe 
            transparent 
            opacity={0.9}
          />
        </mesh>

        <Text
          position={[0, 1.2, 0]}
          fontSize={0.35}
          color="white"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </Text>
      </group>
    </Float>
  );
}