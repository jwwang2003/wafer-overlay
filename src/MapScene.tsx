import { useRef, useEffect, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  CSS2DRenderer,
  CSS2DObject,
} from "three/addons/renderers/CSS2DRenderer.js";
import "./MapScene.css";

import surfaceData from "./输出衬底/1-86107919CNF1/surface.json";
import plData from "./输出衬底/1-86107919CNF1/PL.json";

interface DefectData {
  "X(mm)": number;
  "Y(mm)": number;
  "W(um)": number;
  "H(um)": number;
  Class: string;
}

interface DefectGroup {
  objects: THREE.Mesh[];
  rawData: DefectData[];
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

type FileType = "surface" | "pl";

const easeOutQuad = (t: number): number => t * (2 - t);

const animateProperty = (
  start: number,
  end: number,
  duration: number,
  update: (value: number) => void
) => {
  const startTime = performance.now();

  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easedProgress = easeOutQuad(progress);
    const value = start + (end - start) * easedProgress;

    update(value);

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };
  requestAnimationFrame(animate);
};

const MapScene = () => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [loadingStatus, setLoadingStatus] = useState("加载中...");
  const [currentFile, setCurrentFile] = useState<FileType>("surface");
  const [isPanning, setIsPanning] = useState(false);

  // 缩放控制相关状态
  const [zoomLevel, setZoomLevel] = useState(4.2);
  const [minZoom, setMinZoom] = useState(4);
  const [maxZoom, setMaxZoom] = useState(5);

  const defectGroups = useRef<{
    [key in FileType]: DefectGroup;
  }>({
    surface: { objects: [], rawData: [], minX: 0, maxX: 0, minY: 0, maxY: 0 },
    pl: { objects: [], rawData: [], minX: 0, maxX: 0, minY: 0, maxY: 0 },
  });

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const labelRendererRef = useRef<CSS2DRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const gridObjects = useRef<THREE.Object3D[]>([]);
  const coordinateLabels = useRef<CSS2DObject[]>([]);
  const gridSize = 5;

  const classColorMap = [
    { class: "Unclassified", color: 0xff0000 },
    { class: "Particle", color: 0x000000 },
    { class: "Pit", color: 0x00ff00 },
    { class: "Bump", color: 0xadaf08 },
    { class: "MicroPipe", color: 0x0000ff },
    { class: "Line", color: 0x00ffff },
    { class: "carrot", color: 0xff92f8 },
    { class: "triangle", color: 0xc15dd7f6 },
    { class: "Downfall", color: 0x0000ff },
    { class: "scratch", color: 0xc15dd7f6 },
    { class: "PL_Black", color: 0xff9a16 },
    { class: "PL_White", color: 0xff007b },
    { class: "PL_BPD", color: 0x38d1ff },
    { class: "PL_SF", color: 0x6d6df2 },
    { class: "PL_BSF", color: 0xff92f8 },
  ];

  const renderLegend = () => {
    const uniqueClasses = [...new Set(classColorMap.map((item) => item.class))];
    return (
      <div
        id="legend"
        style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          background: "white",
          padding: "10px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          zIndex: 100,
        }}
      >
        {uniqueClasses.map((className) => {
          const item = classColorMap.find((i) => i.class === className);
          if (!item) return null;
          const colorHex = item.color.toString(16).padStart(6, "0");
          return (
            <div
              key={className}
              style={{ display: "flex", alignItems: "center", margin: "3px 0" }}
            >
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  backgroundColor: `#${colorHex}`,
                  marginRight: "5px",
                  border: "1px solid #999",
                }}
              ></div>
              <span style={{ fontSize: "12px" }}>{item.class}</span>
            </div>
          );
        })}
      </div>
    );
  };

  const createCoordinateLabel = (x: number, y: number) => {
    const div = document.createElement("div");
    div.textContent = `(${x.toFixed(1)}, ${y.toFixed(1)})`;
    div.style.color = "#333";
    div.style.fontSize = "12px";
    div.style.fontFamily = "Arial";
    div.style.pointerEvents = "none";
    div.style.backgroundColor = "rgba(255, 255, 255, 0.7)";
    div.style.padding = "1px 4px";
    div.style.borderRadius = "2px";

    const label = new CSS2DObject(div);
    label.position.set(x, y, 0.5);
    return label;
  };

  const updateCameraZoom = (level: number) => {
    if (!cameraRef.current || !mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    cameraRef.current.left = -width / 2 / level;
    cameraRef.current.right = width / 2 / level;
    cameraRef.current.top = height / 2 / level;
    cameraRef.current.bottom = -height / 2 / level;
    cameraRef.current.updateProjectionMatrix();
  };

  const handleZoomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newLevel = parseFloat(e.target.value);
    setZoomLevel(newLevel);
    updateCameraZoom(newLevel);
  };

  // 重置视图到初始位置
  const resetView = () => {
    if (
      !cameraRef.current ||
      !controlsRef.current ||
      !defectGroups.current[currentFile]
    )
      return;

    const fileData = defectGroups.current[currentFile];
    const targetX = (fileData.minX + fileData.maxX) / 2;
    const targetY = (fileData.minY + fileData.maxY) / 2;
    const targetZoom = minZoom;
    const duration = 500;

    animateProperty(cameraRef.current.position.x, targetX, duration, (x) => {
      cameraRef.current!.position.x = x;
    });
    animateProperty(cameraRef.current.position.y, targetY, duration, (y) => {
      cameraRef.current!.position.y = y;
    });

    animateProperty(controlsRef.current.target.x, targetX, duration, (x) => {
      controlsRef.current!.target.x = x;
      controlsRef.current!.update();
    });
    animateProperty(controlsRef.current.target.y, targetY, duration, (y) => {
      controlsRef.current!.target.y = y;
      controlsRef.current!.update();
    });

    animateProperty(zoomLevel, targetZoom, duration, (level) => {
      setZoomLevel(level);
      updateCameraZoom(level);
      if (controlsRef.current) {
        controlsRef.current.reset();
        controlsRef.current.update();
      }
    });
  };

  const initScene = () => {
    if (!mountRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf5f5f5);
    sceneRef.current = scene;

    const camera = new THREE.OrthographicCamera(
      width / -2,
      width / 2,
      height / 2,
      height / -2,
      0.1,
      1000
    );
    camera.position.z = 10;
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.domElement.style.position = "absolute";
    renderer.domElement.style.top = "0";
    renderer.domElement.style.cursor = "grab";
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(width, height);
    labelRenderer.domElement.style.position = "absolute";
    labelRenderer.domElement.style.top = "0";
    // labelRenderer.domElement.style.pointerEvents = "none";
    mountRef.current.appendChild(labelRenderer.domElement);
    labelRendererRef.current = labelRenderer;

    const controls = new OrbitControls(camera, labelRenderer.domElement);
    controls.enableRotate = false; // 禁用旋转
    controls.enableZoom = true; // 启用缩放（可禁用）
    controls.enablePan = true; // 启用平移
    controls.panSpeed = 2; // 平移速度
    controls.screenSpacePanning = true; // 2D平移模式
    controls.keyPanSpeed = 100.0; // 键盘平移速度

    controls.mouseButtons = {
      LEFT: THREE.MOUSE.PAN, // 左键平移
      MIDDLE: THREE.MOUSE.DOLLY, // 中键缩放
      RIGHT: THREE.MOUSE.ROTATE, // 右键旋转（已禁用）
    };

    controls.addEventListener("start", () => {
      if (controls.action === "pan") {
        setIsPanning(true);
        renderer.domElement.style.cursor = "grabbing";
      } else if (controls.action === "zoom") {
        renderer.domElement.style.cursor = "zoom-in";
      }
    });

    controls.addEventListener("end", () => {
      setIsPanning(false);
      renderer.domElement.style.cursor = "grab";
    });

    controls.addEventListener("zoom", () => {
      if (cameraRef.current && mountRef.current) {
        const width = mountRef.current.clientWidth;
        const newZoom = width / 2 / Math.abs(cameraRef.current.right);
        const clampedZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));
        if (Math.abs(zoomLevel - clampedZoom) > 0.01) {
          setZoomLevel(clampedZoom);
          updateCameraZoom(clampedZoom);
        }
      }
    });

    controlsRef.current = controls;

    // 键盘平移 (方向键)
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!cameraRef.current || !controlsRef.current) return;
      const panAmount = 20 / zoomLevel;

      switch (event.key) {
        case "w":
        case "W":
          cameraRef.current.position.y += panAmount;
          controlsRef.current.target.y += panAmount;
          break;
        case "s":
        case "S":
          cameraRef.current.position.y -= panAmount;
          controlsRef.current.target.y -= panAmount;
          break;
        case "a":
        case "A":
          cameraRef.current.position.x -= panAmount;
          controlsRef.current.target.x -= panAmount;
          break;
        case "d":
        case "D":
          cameraRef.current.position.x += panAmount;
          controlsRef.current.target.x += panAmount;
          break;
        case "R":
        case "r":
          resetView();
          break;
      }
      controlsRef.current.update();
    };

    window.addEventListener("keydown", handleKeyDown);

    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
      labelRenderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (
        !mountRef.current ||
        !cameraRef.current ||
        !rendererRef.current ||
        !labelRendererRef.current
      )
        return;

      const newWidth = mountRef.current.clientWidth;
      const newHeight = mountRef.current.clientHeight;

      updateCameraZoom(zoomLevel);

      rendererRef.current.setSize(newWidth, newHeight);
      labelRendererRef.current.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("keydown", handleKeyDown);
      if (mountRef.current && rendererRef.current && labelRendererRef.current) {
        mountRef.current.removeChild(rendererRef.current.domElement);
        mountRef.current.removeChild(labelRendererRef.current.domElement);
      }
      renderer.dispose();
    };
  };

  const processData = (data: any[], fileType: FileType) => {
    try {
      if (!Array.isArray(data)) {
        throw new Error("数据格式不正确，应为数组");
      }

      const defectObjects: THREE.Mesh[] = [];
      let minX = Infinity,
        maxX = -Infinity;
      let minY = Infinity,
        maxY = -Infinity;

      data.forEach((item: any) => {
        if (!item.hasOwnProperty("X(mm)") || !item.hasOwnProperty("Y(mm)")) {
          console.warn("跳过不完整的记录:", item);
          return;
        }

        const x = parseFloat(item["X(mm)"].toString()) || 0;
        const y = parseFloat(item["Y(mm)"].toString()) || 0;
        const width = parseFloat(item["W(um)"]?.toString() || "0") / 300;
        const height = parseFloat(item["H(um)"]?.toString() || "0") / 300;
        const className = item["Class"] || "Unknown";

        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);

        const colorItem = classColorMap.find((c) => c.class === className);
        const color = colorItem?.color || 0xff00ff;

        const geometry = new THREE.PlaneGeometry(width || 0.5, height || 0.5);
        const material = new THREE.MeshBasicMaterial({
          color: color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8,
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, 0);
        defectObjects.push(mesh);
      });

      if (mountRef.current) {
        const width = mountRef.current.clientWidth;
        // 最小缩放
        const calculatedMinZoom = 4.0;
        // 最大缩放
        const calculatedMaxZoom = width / (gridSize * 2);

        setMinZoom(calculatedMinZoom);
        setMaxZoom(calculatedMaxZoom);
        setZoomLevel(calculatedMinZoom);
      }

      return {
        objects: defectObjects,
        rawData: data as DefectData[],
        minX,
        maxX,
        minY,
        maxY,
      };
    } catch (error) {
      setLoadingStatus(
        `处理 ${fileType} 数据失败: ${(error as Error).message}`
      );
      console.error(`处理 ${fileType} 数据失败:`, error);
      return {
        objects: [],
        rawData: [],
        minX: 0,
        maxX: 0,
        minY: 0,
        maxY: 0,
      };
    }
  };

  const createGrid = (
    minX: number,
    maxX: number,
    minY: number,
    maxY: number,
    defects: DefectData[]
  ) => {
    if (!sceneRef.current) return;

    gridObjects.current.forEach((obj) => sceneRef.current!.remove(obj));
    coordinateLabels.current.forEach((label) =>
      sceneRef.current!.remove(label)
    );
    gridObjects.current = [];
    coordinateLabels.current = [];

    const overlapColor = 0xff7878;
    const baseGridColor = 0x8cefa1;

    const maxGridX = Math.ceil(
      Math.max(Math.abs(minX), Math.abs(maxX)) / gridSize
    );
    const maxGridY = Math.ceil(
      Math.max(Math.abs(minY), Math.abs(maxY)) / gridSize
    );
    const offsetX = gridSize / 2;
    const offsetY = gridSize / 2;

    const gridMaterial = new THREE.MeshBasicMaterial({
      color: baseGridColor,
      opacity: 0.3,
      side: THREE.DoubleSide,
    });

    const borderMaterial = new THREE.LineBasicMaterial({
      color: 0xffffff,
      linewidth: 1,
    });

    for (let i = -maxGridX; i <= maxGridX; i++) {
      for (let j = -maxGridY; j <= maxGridY; j++) {
        const distance = Math.sqrt(
          Math.pow(i / maxGridX, 2) + Math.pow(j / maxGridY, 2)
        );
        if (distance <= 1.0) {
          const gridX = i * gridSize + offsetX;
          const gridY = j * gridSize + offsetY;
          const gridMinX = gridX - gridSize / 2;
          const gridMaxX = gridX + gridSize / 2;
          const gridMinY = gridY - gridSize / 2;
          const gridMaxY = gridY + gridSize / 2;

          // 检查网格是否与缺陷重叠
          const hasOverlap = defects.some((defect) => {
            const x = parseFloat(defect["X(mm)"].toString()) || 0;
            const y = parseFloat(defect["Y(mm)"].toString()) || 0;
            return (
              x >= gridMinX && x <= gridMaxX && y >= gridMinY && y <= gridMaxY
            );
          });

          const material = hasOverlap
            ? new THREE.MeshBasicMaterial({
                color: overlapColor,
                transparent: true,
                opacity: 0.5,
                side: THREE.DoubleSide,
              })
            : gridMaterial;

          // 创建网格平面
          const geometry = new THREE.PlaneGeometry(gridSize, gridSize);
          const mesh = new THREE.Mesh(geometry, material);
          mesh.position.set(gridX, gridY, -0.1);
          sceneRef.current.add(mesh);
          gridObjects.current.push(mesh);

          // 添加网格边框
          const edges = new THREE.EdgesGeometry(geometry);
          const border = new THREE.LineSegments(edges, borderMaterial);
          border.position.copy(mesh.position);
          border.renderOrder = 1;
          sceneRef.current.add(border);
          gridObjects.current.push(border);

          // 创建并添加坐标标签
          // if (i % 2 === 0 && j % 2 === 0) {
          //   const label = createCoordinateLabel(gridX, gridY);
          //   sceneRef.current.add(label);
          //   coordinateLabels.current.push(label);
          // }
        }
      }
    }
  };

  const showFile = (fileType: FileType) => {
    if (!sceneRef.current || !cameraRef.current || !controlsRef.current) return;

    const currentObjects = defectGroups.current[currentFile]?.objects || [];
    currentObjects.forEach((obj) => sceneRef.current!.remove(obj));

    const newObjects = defectGroups.current[fileType]?.objects || [];
    newObjects.forEach((obj) => sceneRef.current!.add(obj));

    const fileData = defectGroups.current[fileType];
    if (fileData?.rawData?.length) {
      createGrid(
        fileData.minX,
        fileData.maxX,
        fileData.minY,
        fileData.maxY,
        fileData.rawData
      );

      const centerX = (fileData.minX + fileData.maxX) / 2;
      const centerY = (fileData.minY + fileData.maxY) / 2;

      cameraRef.current.position.x = centerX;
      cameraRef.current.position.y = centerY;
      controlsRef.current.target.set(centerX, centerY, 0);
      controlsRef.current.update();

      updateCameraZoom(zoomLevel);
    }

    setCurrentFile(fileType);
  };

  useEffect(() => {
    const cleanup = initScene();

    defectGroups.current.surface = processData(surfaceData, "surface");
    defectGroups.current.pl = processData(plData, "pl");
    setLoadingStatus(`
      Surface：${defectGroups.current.surface.rawData.length}个缺陷 | PL：${defectGroups.current.pl.rawData.length}个缺陷<br>
      - 鼠标滚轮：缩放<br>
      - 鼠标左键拖动：平移<br>
      - 键盘(wasd)：平移<br>
    `);

    setTimeout(() => {
      showFile(currentFile);
    }, 100);

    return cleanup;
  }, []);

  useEffect(() => {
    setZoomLevel(Math.max(minZoom, Math.min(maxZoom, zoomLevel)));
  }, [minZoom, maxZoom]);

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative" }}>
      <div
        id="info"
        style={{
          position: "fixed",
          top: "20px",
          left: "20px",
          background: "white",
          padding: "10px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          zIndex: 100,
        }}
        dangerouslySetInnerHTML={{ __html: loadingStatus }}
      />

      {renderLegend()}

      {/* 文件控制按钮 */}
      <div
        style={{
          position: "fixed",
          top: "20px",
          left: "50%",
          transform: "translateX(-50%)",
          background: "white",
          padding: "10px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          zIndex: 100,
          display: "flex",
          gap: "10px",
        }}
      >
        <button
          style={{
            padding: "5px 10px",
            cursor: "pointer",
            backgroundColor:
              currentFile === "surface" ? "#969ea7ff" : "#f0f0f0",
            border: "1px solid #ccc",
            borderRadius: "3px",
          }}
          onClick={() => showFile("surface")}
        >
          Surface defect list
        </button>
        <button
          style={{
            padding: "5px 10px",
            cursor: "pointer",
            backgroundColor: currentFile === "pl" ? "#969ea7ff" : "#f0f0f0",
            border: "1px solid #ccc",
            borderRadius: "3px",
          }}
          onClick={() => showFile("pl")}
        >
          PL defect list
        </button>
        <button
          style={{
            padding: "5px 10px",
            cursor: "pointer",
            backgroundColor: "#f0f0f0",
            border: "1px solid #ccc",
            borderRadius: "3px",
          }}
          onClick={resetView}
        >
          重置视图(R)
        </button>
      </div>

      {/* 缩放控制滑块 */}
      <div
        style={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          background: "white",
          padding: "10px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          zIndex: 100,
        }}
      >
        <label
          style={{ display: "block", marginBottom: "5px", fontSize: "12px" }}
        >
          缩放: {zoomLevel.toFixed(2)}x
        </label>
        <input
          type="range"
          min={minZoom}
          max={maxZoom}
          step={(maxZoom - minZoom) / 100}
          value={zoomLevel}
          onChange={handleZoomChange}
          style={{ width: "200px" }}
        />
      </div>
      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

export default MapScene;