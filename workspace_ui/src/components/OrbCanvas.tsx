import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const palette: Record<string, [number, number, number]> = {
  Idle: [0xf7a53b, 0xffd486, 0x6e4318],
  Listening: [0x53c8ff, 0xc5efff, 0x164b68],
  Transcribing: [0xe0bc59, 0xffe8a5, 0x604b16],
  Thinking: [0xc071ff, 0xf0d4ff, 0x4c176f],
  Speaking: [0x70e7a2, 0xd6ffe6, 0x1d6138],
  Error: [0xff5c57, 0xffc0b8, 0x711e1b],
  Disabled: [0x68727e, 0xb5bbc2, 0x252c34],
}

export default function OrbCanvas({ state = 'Idle' }: { state?: string }) {
  const mountRef = useRef<HTMLDivElement>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100)
    camera.position.z = 4.6
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    const coreMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xf7a53b, emissive: 0xf7a53b, emissiveIntensity: 2.6,
      roughness: 0.18, metalness: 0.15, transparent: true, opacity: 0.95,
    })
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.62, 4), coreMaterial)
    group.add(core)

    const shellMaterial = new THREE.MeshBasicMaterial({ color: 0xf7a53b, wireframe: true, transparent: true, opacity: 0.20 })
    const shell = new THREE.Mesh(new THREE.IcosahedronGeometry(1.05, 2), shellMaterial)
    group.add(shell)

    const ringMaterial = new THREE.MeshBasicMaterial({ color: 0xffc466, transparent: true, opacity: 0.78, side: THREE.DoubleSide })
    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(1.33, 0.025, 12, 180, Math.PI * 1.45), ringMaterial)
    ring1.rotation.x = 0.8
    group.add(ring1)
    const ring2 = ring1.clone()
    ring2.rotation.x = -0.8
    ring2.rotation.y = 0.5
    group.add(ring2)

    const count = 420
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 1.6 + Math.random() * 1.5
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)
    }
    const particleGeometry = new THREE.BufferGeometry()
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particleMaterial = new THREE.PointsMaterial({ size: 0.018, color: 0xf7a53b, transparent: true, opacity: 0.38 })
    const particles = new THREE.Points(particleGeometry, particleMaterial)
    scene.add(particles)

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = mount
      renderer.setSize(Math.max(10, w), Math.max(10, h), false)
      camera.aspect = Math.max(0.1, w / Math.max(1, h))
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(mount)
    resize()

    let raf = 0
    const clock = new THREE.Clock()
    const animate = () => {
      const t = clock.getElapsedTime()
      const [primary, highlight] = palette[stateRef.current] || palette.Idle
      coreMaterial.color.setHex(primary)
      coreMaterial.emissive.setHex(primary)
      shellMaterial.color.setHex(primary)
      ringMaterial.color.setHex(highlight)
      particleMaterial.color.setHex(primary)
      const active = stateRef.current !== 'Idle' && stateRef.current !== 'Disabled'
      const pulse = 1 + Math.sin(t * (active ? 5.2 : 1.6)) * (active ? 0.065 : 0.025)
      core.scale.setScalar(pulse)
      core.rotation.y = t * 0.33
      core.rotation.x = Math.sin(t * 0.31) * 0.18
      shell.rotation.y = -t * 0.18
      shell.rotation.z = t * 0.12
      ring1.rotation.z = t * 0.44
      ring2.rotation.z = -t * 0.36
      particles.rotation.y = t * 0.025
      particles.rotation.x = Math.sin(t * 0.1) * 0.04
      renderer.render(scene, camera)
      raf = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      renderer.dispose()
      particleGeometry.dispose()
      core.geometry.dispose(); shell.geometry.dispose(); ring1.geometry.dispose()
      coreMaterial.dispose(); shellMaterial.dispose(); ringMaterial.dispose(); particleMaterial.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [])

  return <div className="orb-canvas" ref={mountRef} />
}
