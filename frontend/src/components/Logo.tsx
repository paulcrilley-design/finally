import Image from "next/image";
import logo from "../assets/openui-logo.png";

/**
 * The openUI logo, as in the pm app (140px in the header, 172px on the sign-in
 * card). Imported rather than served from public/ so the URL gets the basePath
 * when the site runs under a sub-path; `unoptimized` because a static export
 * has no image optimizer.
 */
export function Logo({ width = 140, className }: { width?: number; className?: string }) {
  return (
    <Image
      src={logo}
      alt="openUI"
      width={width}
      priority
      unoptimized
      className={className}
      style={{ height: "auto", width }}
    />
  );
}
