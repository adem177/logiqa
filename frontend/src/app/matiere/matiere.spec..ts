import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { CoursContentComponent } from '../matiere/matiere';
import { CourseService } from '../services/course.service';

describe('CoursContentComponent', () => {
  let component: CoursContentComponent;
  let fixture: ComponentFixture<CoursContentComponent>;
  let httpMock: HttpTestingController;

  // Mock de CourseService : aucun cours dynamique, on retombera sur COURSES_DETAILS
  const courseServiceMock = {
    courses: () => []
  };

  // Mock du Router (pour goBack() / navigate())
  const routerMock = {
    navigate: vi.fn()
  };

  // Mock de la route active : simule /cours/:id avec id = 1
  const activatedRouteMock = {
    snapshot: {
      paramMap: convertToParamMap({ id: '1' })
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CoursContentComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: CourseService, useValue: courseServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: activatedRouteMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(CoursContentComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load a static course when no dynamic course matches the id', () => {
    // Si un cours avec id=1 existe dans COURSES_DETAILS, il doit être chargé
    expect(component.course()).toBeTruthy();
  });

  it('should toggle chapter expansion', () => {
    const chapterId = 1;
    expect(component.isExpanded(chapterId)).toBe(false);

    component.toggleChapter(chapterId);
    expect(component.isExpanded(chapterId)).toBe(true);

    component.toggleChapter(chapterId);
    expect(component.isExpanded(chapterId)).toBe(false);
  });

  it('should switch between video and pdf resource view', () => {
    const chapterId = 1;
    expect(component.getResourceView(chapterId)).toBe('video');

    component.setResourceView(chapterId, 'pdf');
    expect(component.getResourceView(chapterId)).toBe('pdf');
  });

  it('should reject a non-PDF file when uploading a PDF resource', () => {
    const chapterId = 1;
    const fakeFile = new File(['contenu'], 'image.png', { type: 'image/png' });
    const event = {
      target: { files: [fakeFile], value: '' }
    } as unknown as Event;

    component.onFileSelected(event, chapterId, 'pdf');

    expect(component.uploadError(chapterId)).toBe('Le fichier doit être un PDF.');
  });

  it('should send a POST request and update counts on successful video upload', () => {
    const chapterId = 1;
    const fakeFile = new File(['contenu'], 'lecon1.mp4', { type: 'video/mp4' });
    const event = {
      target: { files: [fakeFile], value: '' }
    } as unknown as Event;

    const beforeCount = component
      .chapters()
      .find(c => c.id === chapterId)?.videosCount ?? 0;

    component.onFileSelected(event, chapterId, 'video');

    const req = httpMock.expectOne(`/api/chapitres/${chapterId}/upload`);
    expect(req.request.method).toBe('POST');
    req.flush({ success: true });

    const afterCount = component
      .chapters()
      .find(c => c.id === chapterId)?? 0;

    expect(afterCount).toBe(beforeCount + 1);
  });

  afterEach(() => {
    httpMock.verify();
  });
});