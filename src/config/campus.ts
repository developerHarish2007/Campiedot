// Set after confirming the campus. These values currently point to SRM Easwari, Ramapuram.
export const campusConfig = {
  id: import.meta.env.VITE_CAMPUS_ID ?? 'srm-easwari-demo',
  name: import.meta.env.VITE_CAMPUS_NAME ?? 'SRM Easwari Engineering College',
  center: [Number(import.meta.env.VITE_CAMPUS_LNG ?? 80.17934), Number(import.meta.env.VITE_CAMPUS_LAT ?? 13.03358)] as [number, number],
  zoom: 17,
};
