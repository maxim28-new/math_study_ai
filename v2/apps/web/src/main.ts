import { bootWorkshop } from "./app.ts";
import "./styles.css";

const canvas = document.querySelector<HTMLCanvasElement>("#workshop");
if (!canvas) {
  throw new Error("workshop canvas missing");
}

bootWorkshop(canvas);
