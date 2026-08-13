import { describe, it, expect, beforeEach } from 'vitest';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CoursContentComponent } from '../matiere/matiere_python';

describe('CoursContentComponent', () => {
  let component: CoursContentComponent;
  let fixture: ComponentFixture<CoursContentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CoursContentComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(CoursContentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});