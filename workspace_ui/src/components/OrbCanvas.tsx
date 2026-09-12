import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const stateEnergy: Record<string, { speed:number, pulse:number, accent:number }> = {
  Idle: { speed:.45, pulse:.018, accent:0xffb23f },
  Listening: { speed:1.05, pulse:.055, accent:0x65d8ff },
  Transcribing: { speed:1.25, pulse:.045, accent:0xffd978 },
  Thinking: { speed:1.7, pulse:.07, accent:0xffca55 },
  Speaking: { speed:1.35, pulse:.065, accent:0xffe2a0 },
  Error: { speed:.8, pulse:.08, accent:0xff5a45 },
  Disabled: { speed:.12, pulse:.006, accent:0x7b6950 },
}

function glowTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const ctx = c.getContext('2d')!
  const g = ctx.createRadialGradient(128,128,0,128,128,128)
  g.addColorStop(0,'rgba(255,245,205,1)')
  g.addColorStop(.12,'rgba(255,194,72,.95)')
  g.addColorStop(.34,'rgba(245,125,20,.34)')
  g.addColorStop(.72,'rgba(236,104,10,.07)')
  g.addColorStop(1,'rgba(0,0,0,0)')
  ctx.fillStyle=g; ctx.fillRect(0,0,256,256)
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function circularPoints(radius:number, count:number, wobble=0) {
  const pts: THREE.Vector3[] = []
  for (let i=0;i<count;i++) {
    const a=(i/count)*Math.PI*2
    const r=radius + Math.sin(a*5)*wobble
    pts.push(new THREE.Vector3(Math.cos(a)*r, Math.sin(a)*r, Math.sin(a*3)*wobble*.7))
  }
  return pts
}

export default function OrbCanvas({ state = 'Idle' }: { state?: string }) {
  const mountRef = useRef<HTMLDivElement>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42,1,.1,100)
    camera.position.set(0,0,5.25)
    const renderer = new THREE.WebGLRenderer({ alpha:true, antialias:true, powerPreference:'high-performance' })
    renderer.setPixelRatio(Math.min(devicePixelRatio,2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.setClearColor(0x000000,0)
    mount.appendChild(renderer.domElement)

    const root = new THREE.Group()
    root.rotation.x = -.1
    scene.add(root)

    const amber = 0xf49b24
    const gold = 0xffc85a
    const dimAmber = 0x7e3b08

    // Dark metallic core with a hot luminous center: closer to the cinematic
    // JARVIS hologram than the old solid glowing ball.
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(.56,48,48),
      new THREE.MeshPhysicalMaterial({
        color:0x171009, metalness:.8, roughness:.22,
        emissive:0xe56f0d, emissiveIntensity:1.2,
        transparent:true, opacity:.93,
      }),
    )
    root.add(core)

    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map:glowTexture(), color:gold, transparent:true, blending:THREE.AdditiveBlending, depthWrite:false, opacity:.95 }))
    glow.scale.set(2.65,2.65,1)
    root.add(glow)

    const innerShell = new THREE.Mesh(
      new THREE.IcosahedronGeometry(.83,3),
      new THREE.MeshBasicMaterial({ color:gold, wireframe:true, transparent:true, opacity:.14, blending:THREE.AdditiveBlending }),
    )
    root.add(innerShell)

    const outerShell = new THREE.Mesh(
      new THREE.IcosahedronGeometry(1.18,2),
      new THREE.MeshBasicMaterial({ color:amber, wireframe:true, transparent:true, opacity:.075, blending:THREE.AdditiveBlending }),
    )
    root.add(outerShell)

    const rings: THREE.Mesh[] = []
    const ringConfigs = [
      [1.02,.012,.7,.18,0], [1.23,.018,1.1,-.4,.2], [1.43,.014,.28,.9,-.35],
      [.91,.01,1.55,.35,.5], [1.58,.009,.92,.15,.85],
    ]
    for (const [r,t,rx,ry,rz] of ringConfigs) {
      const mat = new THREE.MeshBasicMaterial({ color:amber, transparent:true, opacity:.54, side:THREE.DoubleSide, blending:THREE.AdditiveBlending })
      const arc = new THREE.Mesh(new THREE.TorusGeometry(r,t,8,160,Math.PI*(1.1+Math.random()*.72)),mat)
      arc.rotation.set(rx,ry,rz)
      rings.push(arc); root.add(arc)
    }

    // Thin HUD latitude/longitude traces.
    const traces: THREE.Line[] = []
    for (let i=0;i<8;i++) {
      const geo = new THREE.BufferGeometry().setFromPoints(circularPoints(1.05+i*.055,90,.01))
      const line = new THREE.Line(geo,new THREE.LineBasicMaterial({ color:i%3===0?gold:dimAmber,transparent:true,opacity:i%3===0?.28:.13,blending:THREE.AdditiveBlending }))
      line.rotation.set(Math.random()*Math.PI,Math.random()*Math.PI,Math.random()*Math.PI)
      traces.push(line); root.add(line)
    }

    // Orbiting data nodes and tiny connector sparks.
    const nodeGroup = new THREE.Group(); root.add(nodeGroup)
    for (let i=0;i<42;i++) {
      const phi=Math.acos(2*Math.random()-1), theta=Math.random()*Math.PI*2, r=1.32+Math.random()*.32
      const node=new THREE.Mesh(new THREE.SphereGeometry(.012+Math.random()*.017,8,8),new THREE.MeshBasicMaterial({color:i%8===0?0xffe8b0:amber,transparent:true,opacity:.55+Math.random()*.35}))
      node.position.set(r*Math.sin(phi)*Math.cos(theta),r*Math.sin(phi)*Math.sin(theta),r*Math.cos(phi))
      nodeGroup.add(node)
    }

    const count=620
    const positions=new Float32Array(count*3)
    for (let i=0;i<count;i++) {
      const r=1.75+Math.random()*1.35, theta=Math.random()*Math.PI*2, phi=Math.acos(2*Math.random()-1)
      positions[i*3]=r*Math.sin(phi)*Math.cos(theta)
      positions[i*3+1]=r*Math.sin(phi)*Math.sin(theta)
      positions[i*3+2]=r*Math.cos(phi)
    }
    const pgeo=new THREE.BufferGeometry(); pgeo.setAttribute('position',new THREE.BufferAttribute(positions,3))
    const pmat=new THREE.PointsMaterial({size:.014,color:amber,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false})
    const particles=new THREE.Points(pgeo,pmat); scene.add(particles)

    // Small scanning halo gives the sphere the layered data-globe look without
    // copying any Marvel asset directly.
    const scan = new THREE.Mesh(new THREE.TorusGeometry(1.72,.008,6,220),new THREE.MeshBasicMaterial({color:gold,transparent:true,opacity:.22,blending:THREE.AdditiveBlending}))
    scan.rotation.x=Math.PI/2; root.add(scan)

    const resize=()=>{
      const w=Math.max(10,mount.clientWidth),h=Math.max(10,mount.clientHeight)
      renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix()
    }
    const ro=new ResizeObserver(resize); ro.observe(mount); resize()

    let raf=0
    const clock=new THREE.Clock()
    const animate=()=>{
      const t=clock.getElapsedTime()
      const energy=stateEnergy[stateRef.current] || stateEnergy.Idle
      const pulse=1+Math.sin(t*(1.5+energy.speed*2.2))*energy.pulse
      core.scale.setScalar(pulse)
      ;(core.material as THREE.MeshPhysicalMaterial).emissiveIntensity=1.05+(stateRef.current==='Speaking'?Math.max(0,Math.sin(t*8))*1.3:Math.max(0,Math.sin(t*2.1))*.45)
      ;(glow.material as THREE.SpriteMaterial).color.setHex(energy.accent)
      glow.scale.setScalar(2.55+Math.sin(t*2.3)*.08+(stateRef.current==='Thinking'?.18:0))
      innerShell.rotation.y=t*.18*energy.speed; innerShell.rotation.x=Math.sin(t*.21)*.2
      outerShell.rotation.y=-t*.095*energy.speed; outerShell.rotation.z=t*.07
      rings.forEach((ring,i)=>{ ring.rotation.z += .0014*(i%2?1:-1)*energy.speed; ring.rotation.y += .0005*(i+1)*energy.speed })
      traces.forEach((line,i)=>{ line.rotation.z += .00022*(i+1)*energy.speed })
      nodeGroup.rotation.y=t*.06*energy.speed; nodeGroup.rotation.x=Math.sin(t*.09)*.12
      scan.rotation.z=t*.22*energy.speed
      particles.rotation.y=t*.012; particles.rotation.x=Math.sin(t*.07)*.04
      renderer.render(scene,camera); raf=requestAnimationFrame(animate)
    }
    animate()

    return ()=>{
      cancelAnimationFrame(raf); ro.disconnect(); renderer.dispose(); pgeo.dispose()
      mount.removeChild(renderer.domElement)
    }
  },[])

  return <div className="orb-canvas" ref={mountRef}/>
}
