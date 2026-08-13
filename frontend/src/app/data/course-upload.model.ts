export interface ChapterUpload {
  id: number;
  title: string;
  videos: File[];
  pdfs: File[];
}

export interface SectionUpload {
  id: number;
  title: string;
  chapters: ChapterUpload[];
}