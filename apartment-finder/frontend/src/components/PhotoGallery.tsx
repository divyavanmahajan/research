interface Props {
  photos: string[];
}

export default function PhotoGallery({ photos }: Props) {
  if (!photos.length) {
    return (
      <div className="h-56 bg-gray-100 rounded-xl flex items-center justify-center text-gray-400">
        No photos available
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 snap-x snap-mandatory">
      {photos.map((src, i) => (
        <img
          key={i}
          src={src}
          alt={`Photo ${i + 1}`}
          className="h-56 w-auto flex-shrink-0 rounded-xl object-cover snap-start"
        />
      ))}
    </div>
  );
}
